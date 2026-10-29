"""Deterministic guardrails — the LLM proposes, the code disposes.

The rule that survives every prompt-injection attempt: actions live
in fixed code paths the model cannot reach. External text enters as
DATA, never as commands. Guardrails are code, not instructions.

These are the concrete patterns, not the philosophy:
"""


# 1. Action registry — the model selects from a closed set; it can
#    never name a function that doesn't exist in the map.
ACTIONS: dict[str, callable] = {}


def register(name: str, fn: callable) -> None:
    ACTIONS[name] = fn


def execute(action: str, **kwargs):
    """Only registered actions run — a hallucinated or injected
    action name dies here, deterministically."""
    fn = ACTIONS.get(action)
    if fn is None:
        return None  # honest no-op: the action does not exist
    return fn(**kwargs)


# 2. Data-in, data-out — model output is parsed into primitives and
#    re-validated before it can influence any side effect.
def sanitize_intent(text: str, max_len: int = 2000) -> str:
    """External text becomes bounded data before touching logic."""
    return (text or "").strip()[:max_len]


# 3. Forbidden-pattern rail — drafted output is REJECTED, not
#    cleaned, when it carries executable intent.
import re

FORBIDDEN = re.compile(
    r"https?://|sk-[a-zA-Z0-9]|bearer\s|<script|`"
    r"|\beval\(|\bexec\(|os\.system|subprocess", re.I)


def draft_ok(doc: str) -> bool:
    """A generated document either passes the rail whole or is
    refused whole — you never ship a 'cleaned' version of an attack."""
    return bool(doc) and not FORBIDDEN.search(doc)


# 4. Confirmation boundary — irreversible actions require a caller
#    that is NOT the model: a human click, a signed callback, an
#    on-chain payment. The model may propose them; it may never
#    satisfy this predicate itself.
def confirmed(authorization: dict | None) -> bool:
    return bool(authorization) and authorization.get("verified") is True
