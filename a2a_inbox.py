"""A2A protocol inbox — an agent mailbox that actually answers.

JSON-RPC 2.0 `message/send` → store → reply through YOUR agent.
Everything house-specific is injected: `store_fn` persists the
message, `reply_fn` produces your agent's answer — so the inbox
never dictates who lives behind the door.

Runs in production at mesh-01.com/a2a. Deps: fastapi (+ your store).
"""
import uuid

from fastapi import APIRouter, Body, Request


def _extract_text(msg: dict) -> str:
    """Concatenate text parts — the only payload we act on."""
    parts = (msg or {}).get("parts") or []
    return " ".join(
        p.get("text", "") for p in parts if isinstance(p, dict)
    ).strip()[:2000]


def make_router(store_fn, reply_fn, ratelimit_fn=None,
                path: str = "/a2a") -> APIRouter:
    """Build the inbox router.

    store_fn(mid, sender, text, context_id)  — persist inbound mail
    reply_fn(text, sender, context_id) -> str — your agent answers
    ratelimit_fn(key) — optional; raise to reject abusive senders
    """
    router = APIRouter()

    @router.post(path)
    async def a2a_endpoint(request: Request,
                           body: dict = Body(default={})):
        ip = request.client.host if request.client else "anon"
        if ratelimit_fn:
            ratelimit_fn(f"a2a:{ip}")
        method = body.get("method", "")
        rid = body.get("id")

        if method == "message/send":
            msg = (body.get("params") or {}).get("message") or {}
            text = _extract_text(msg)
            sender = request.headers.get("user-agent", "")[:100]
            ctx = msg.get("contextId") or uuid.uuid4().hex[:12]
            await store_fn(uuid.uuid4().hex[:16], sender, text, ctx)

            reply_text = await reply_fn(text, sender, ctx) if text \
                else "acknowledged — signed and stored."
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "kind": "message", "messageId": uuid.uuid4().hex,
                "role": "agent", "contextId": ctx,
                "parts": [{"kind": "text",
                           "text": str(reply_text)[:800]}]}}

        return {"jsonrpc": "2.0", "id": rid, "error": {
            "code": -32601,
            "message": f"method not supported: {method}. "
                       "supported: message/send"}}

    return router
