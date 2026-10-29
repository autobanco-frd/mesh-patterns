"""x402 payment verification — verify a USDC payment on-chain with
no facilitator, no SDK, no trust in the caller.

Flow: client hits a paid endpoint → 402 + `accepts` → client sends
USDC on-chain → retries with `X-Payment: <tx_hash>` → we read the
transaction receipt and look for a USDC Transfer log to our payTo
with amount >= price. Pure evidence: nothing is taken on the
caller's word, and one hash can only ever pay for one delivery.

Distilled from mesh-01.com production code. Deps: httpx.
"""
import json
import re

import httpx

# keccak256("Transfer(address,address,uint256)") — universal ERC-20
# event signature, constant across chains.
TRANSFER_TOPIC = ("0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a1"
                  "1628f55a4df523b3ef")
_TX_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
RPC_TIMEOUT = 12.0
MIN_CONFIRMATIONS = 1

CHAINS = {
    8453: {"name": "Base",
           "rpcs": ["https://mainnet.base.org",
                    "https://base-rpc.publicnode.com",
                    "https://base.llamarpc.com"],
           "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"},
    42161: {"name": "Arbitrum",
            "rpcs": ["https://arb1.arbitrum.io/rpc"],
            "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"},
    10: {"name": "Optimism",
         "rpcs": ["https://mainnet.optimism.io"],
         "usdc": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85"},
    137: {"name": "Polygon",
          "rpcs": ["https://polygon-rpc.com"],
          "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"},
}


class X402Error(Exception):
    """Payment verification failure with a client-readable reason."""


def usd_to_atomic(usd: float) -> int:
    """USDC has 6 decimals."""
    return int(round(usd * 1_000_000))


def parse_payment_header(value: str | None) -> str | None:
    """X-Payment may be a bare tx hash or a small JSON envelope."""
    if not value:
        return None
    value = value.strip()
    if _TX_RE.match(value):
        return value.lower()
    try:
        obj = json.loads(value)
        tx = (obj.get("tx_hash") or obj.get("txHash")
              or obj.get("transaction") or "")
        return tx.lower() if _TX_RE.match(tx) else None
    except (json.JSONDecodeError, AttributeError):
        return None


def _topic_addr(topic: str) -> str:
    return "0x" + topic[-40:].lower()


def extract_transfer(receipt: dict, payto: str,
                     contract: str) -> dict | None:
    """Find a USDC Transfer to payto inside a tx receipt.
    Returns {payer, amount_atomic} or None."""
    payto, contract = payto.lower(), contract.lower()
    for entry in receipt.get("logs") or []:
        if (entry.get("address") or "").lower() != contract:
            continue
        topics = entry.get("topics") or []
        if len(topics) < 3 or topics[0].lower() != TRANSFER_TOPIC:
            continue
        if _topic_addr(topics[2]) != payto:
            continue
        try:
            amount = int(entry.get("data") or "0x0", 16)
        except (TypeError, ValueError):
            continue
        return {"payer": _topic_addr(topics[1]),
                "amount_atomic": amount}
    return None


async def _rpc_call(method: str, params: list,
                    urls: list) -> object | None:
    """Try each configured RPC in order; first good result wins."""
    body = {"jsonrpc": "2.0", "method": method,
            "params": params, "id": 1}
    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=RPC_TIMEOUT) as c:
                resp = await c.post(url, json=body)
            if resp.status_code != 200:
                continue
            data = resp.json()
            if "result" in data:
                return data["result"]
        except Exception:  # network/json errors → next RPC
            continue
    return None


async def verify_payment(tx_hash: str, min_atomic: int, payto: str,
                         chain_id: int = 8453,
                         min_confs: int = MIN_CONFIRMATIONS) -> dict:
    """Verify a USDC payment on-chain. Returns evidence or raises
    X402Error with the precise reason nothing was accepted."""
    if not _TX_RE.match(tx_hash):
        raise X402Error("malformed tx hash")
    ch = CHAINS.get(chain_id)
    if not ch:
        raise X402Error(f"unsupported chain {chain_id}")
    receipt = await _rpc_call(
        "eth_getTransactionReceipt", [tx_hash], ch["rpcs"])
    if not receipt:
        raise X402Error("transaction not found or not yet mined")
    if receipt.get("status") != "0x1":
        raise X402Error("transaction reverted on-chain")
    transfer = extract_transfer(receipt, payto, ch["usdc"])
    if not transfer:
        raise X402Error(
            "no USDC transfer to payTo in that transaction")
    if transfer["amount_atomic"] < min_atomic:
        raise X402Error(
            f"underpaid: got {transfer['amount_atomic']} atomic USDC, "
            f"need {min_atomic}")
    block = int(receipt.get("blockNumber") or "0x0", 16)
    head = await _rpc_call("eth_blockNumber", [], ch["rpcs"])
    if isinstance(head, str) and head.startswith("0x"):
        confs = int(head, 16) - block + 1
        if confs < min_confs:
            raise X402Error(
                f"unconfirmed: {confs} confirmations, "
                f"need {min_confs}")
    return {"payer": transfer["payer"],
            "amount_atomic": transfer["amount_atomic"],
            "block": block, "tx_hash": tx_hash.lower()}
