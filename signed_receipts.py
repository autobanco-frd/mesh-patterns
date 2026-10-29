"""Signed, hash-chained receipts — proof of work a third party can
verify without trusting you.

Design:
- Canonical JSON (sorted keys, no spaces) — same payload always
  verifies to the same bytes.
- prev_hash chains receipts into a tamper-evident ledger
  ("GENESIS" for the first).
- The payload stores HASHES of result/error — proof of work without
  leaking client payloads.
- Ed25519 signature; the public key is published out-of-band so
  anyone verifies offline.

Deps: cryptography.
"""
import base64
import hashlib
import json
from datetime import datetime, timezone

SPEC = "mesh-receipt/0.1"
GENESIS = "GENESIS"


def canonical(payload: dict) -> bytes:
    """Deterministic serialization — the exact bytes that get signed."""
    return json.dumps(payload, sort_keys=True,
                      separators=(",", ":")).encode()


def receipt_id_for(payload: dict) -> str:
    return "rcpt_" + hashlib.sha256(canonical(payload)).hexdigest()[:24]


def build(node_id: str, key_id: str, task_id: str, engine: str,
          status: str, result_json: str | None, error: str | None,
          duration_ms: float, declared_value: float,
          prev_hash: str = GENESIS) -> dict:
    """Assemble the receipt payload — sign it, then store it."""
    return {
        "spec": SPEC, "node_id": node_id, "key_id": key_id,
        "task_id": task_id, "engine": engine, "status": status,
        "duration_ms": round(duration_ms, 2),
        "result_sha256": (hashlib.sha256(result_json.encode())
                          .hexdigest() if result_json else None),
        "error_sha256": (hashlib.sha256(error.encode()).hexdigest()
                         if error else None),
        "declared_value": declared_value,
        "prev_hash": prev_hash,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }


def verify_receipt(payload: dict, signature_b64: str,
                   pub_b64: str) -> bool:
    """Verify a receipt — offline, zero trust in the issuer."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PublicKey)
    try:
        pub = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(pub_b64))
        pub.verify(base64.b64decode(signature_b64),
                   canonical(payload))
        return True
    except Exception:
        return False
