"""Ed25519 node identity — one key, published once, verifying
everything the node signs.

Production rules baked in:
- seed file is 32 raw bytes, mode 0600, written with O_EXCL so a
  second process can never clobber the node's identity
- env-injected seed (32-byte hex) for ephemeral hosts
- key_id = 'k' + sha256(pubkey)[:12] — the fingerprint that travels
  inside every signed payload so verifiers know WHICH key signed

Deps: cryptography.
"""
import base64
import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey)

_key: Ed25519PrivateKey | None = None


def load_or_generate(seed_hex: str | None = None,
                     path: str | None = None) -> Ed25519PrivateKey:
    """Load the node key: env hex seed → file → generate+persist."""
    global _key
    if _key is not None:
        return _key
    if seed_hex:
        seed = bytes.fromhex(seed_hex)
        if len(seed) != 32:
            raise RuntimeError("seed must be 32-byte hex")
        _key = Ed25519PrivateKey.from_private_bytes(seed)
        return _key
    p = Path(path)
    if p.exists():
        seed = p.read_bytes()
        if len(seed) != 32:
            raise RuntimeError(f"{p} is not a valid Ed25519 seed")
        _key = Ed25519PrivateKey.from_private_bytes(seed)
        return _key
    key = Ed25519PrivateKey.generate()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption()))
    finally:
        os.close(fd)
    _key = key
    return key


def public_key_b64() -> str:
    return base64.b64encode(_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw)).decode()


def key_id() -> str:
    """Fingerprint of the public key — stable and safe to publish."""
    return "k" + hashlib.sha256(
        base64.b64decode(public_key_b64())).hexdigest()[:12]


def sign(payload: bytes) -> str:
    return base64.b64encode(_key.sign(payload)).decode()


def verify(pub_b64: str, sig_b64: str, payload: bytes) -> bool:
    try:
        pub = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(pub_b64))
        pub.verify(base64.b64decode(sig_b64), payload)
        return True
    except Exception:
        return False
