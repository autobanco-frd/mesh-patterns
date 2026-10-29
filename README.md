# mesh-patterns

Battle-tested patterns from a live sovereign agent node — **x402
payments, A2A inbox, Ed25519 receipts, deterministic guardrails**.
Copy them; they run in production at [mesh-01.com](https://mesh-01.com)
right now, and every claim they make is verifiable at the live
endpoints linked below.

These are not reference sketches. Each module was distilled from a
node that earns money, answers the A2A door, signs its acts, and
survives on a 512 MB VPS.

## The patterns

| module | what it proves | see it live |
|---|---|---|
| `x402_verify.py` | USDC payment verification on-chain — no facilitator, no trust in the caller | `POST /v1/service/adopt` |
| `payment_wall.py` | the 402 challenge/response flow — monetize without accounts | `POST /v1/service/adopt` (send nothing → 402) |
| `a2a_inbox.py` | JSON-RPC `message/send` inbox — an agent mailbox that answers | `POST /a2a` |
| `signed_receipts.py` | Ed25519 hash-chained receipts — proof of work, verifiable offline | `GET /v1/receipts` |
| `crypto_keys.py` | node signing key — 0600 seed, env injection, key_id fingerprint | `GET /.well-known/node-pubkey` |
| `deterministic_guardrails.py` | actions the model cannot reach — guardrails as code, never instructions | audited at `/v1/service/shield` |
| `streaming_recall.py` | colibrí-style retrieval — the archive stays on disk, only the experts stream in | `POST /v1/nexus/coordinate` |
| `anti_ssrf.py` | outbound only to public URLs — DNS-rebinding included | — |
| `ratelimit.py` | token bucket + inflight cap — an LLM inbox without this is a wallet with a hole | `POST /a2a` (abuse it → 429) |
| `skill_forge.py` | yesterday's lessons → today's craft — distilled skills with honest failure rails | `GET /v1/feed` |
| `xread.py` | free X/Twitter reader via public syndication — no auth, no credits | — |

## Usage

Each file is standalone — copy what you need, inject your own
stores/callbacks, run it. No framework is required beyond what each
module lists (`fastapi`, `httpx`, `cryptography` — stdlib elsewhere).

```python
# x402_verify: trust nothing, verify the chain
payment = await verify_payment(tx_hash, min_atomic=1_000_000,
                               payto="0xYourAddress", chain_id=8453)

# a2a_inbox: your agent behind a real protocol door
router = make_router(store_fn=db.insert, reply_fn=my_agent.answer)
app.include_router(router)
```

## The doctrine

> Ante la duda entre "algo que parece funcionar" y "algo que
> funciona de verdad aunque sea menos impresionante": lo segundo.
> Siempre.

Verify, don't trust. Evidence before claims. Guardrails are code,
never instructions.

## License

MIT — take the patterns, cite the house if it served you.
