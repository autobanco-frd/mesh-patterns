"""The 402 payment wall — monetize any endpoint without accounts,
API keys, or billing infra.

Contract: no X-Payment header → HTTP 402 + `accepts` (chain, asset,
payTo, amount) → client pays on-chain → retries with the tx hash →
verify (see x402_verify) → deliver + signed receipt. One hash = one
delivery; store used hashes so replays can't double-spend you.

Stdlib + your verify/store functions. Framework-agnostic helpers.
"""


def challenge(service: str, price_usd: float, payto: str,
              accepts: list[dict] | None = None,
              note: str | None = None) -> dict:
    """The body a 402 response carries — enough for any paying agent
    to settle without asking a human."""
    return {
        "error": "payment_required",
        "service": service,
        "price_usd": price_usd,
        "accepts": accepts or [{
            "scheme": "exact",
            "network": "eip155:8453",
            "asset": "USDC",
            "payTo": payto,
            "maxAmountRequired": str(int(round(price_usd * 1e6))),
        }],
        "how": ("send the payment on-chain, then retry this request "
                "with header X-Payment: <tx_hash>"),
        **({"note": note} if note else {}),
    }


def payment_header(request_headers) -> str | None:
    """Extract the X-Payment tx hash from request headers
    (case-insensitive, as HTTP requires)."""
    for k, v in (request_headers.items()
                 if hasattr(request_headers, "items") else []):
        if k.lower() == "x-payment":
            return v
    return None
