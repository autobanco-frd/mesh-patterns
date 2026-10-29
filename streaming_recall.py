"""Streaming recall — colibrí-style context for a small-memory node.

The archive lives on disk; nothing loads wholesale into the prompt.
A query streams in only the 'experts' it needs — keyword-scored
one-line hits — while a small LRU keeps the hot set in RAM.

Swap `sources` for your own stores: each is an async callable
(query_terms, limit) -> list[str] of compact evidence lines.
"""
import re
from collections import OrderedDict

_LRU_CAP = 64
_lru: OrderedDict[str, str] = OrderedDict()

_STOP = {"the", "and", "for", "with", "that", "this", "from", "are",
         "was", "will", "what", "when", "where", "which", "have",
         "been", "their", "they", "them", "into", "about", "would",
         "could", "should", "there", "these", "those"}


def terms(query: str) -> list[str]:
    return sorted({w.lower() for w in
                   re.findall(r"[a-zA-Z]{4,}", query)} - _STOP)[:10]


def score(query_terms: list[str], *parts) -> int:
    text = " ".join(str(p or "").lower() for p in parts)
    return sum(1 for t in query_terms if t in text)


def _cache_get(key: str):
    v = _lru.get(key)
    if v is not None:
        _lru.move_to_end(key)
    return v


def _cache_put(key: str, val: str) -> None:
    _lru[key] = val
    _lru.move_to_end(key)
    if len(_lru) > _LRU_CAP:
        _lru.popitem(last=False)


async def retrieve(query: str, sources: list,
                   scope: str = "", limit: int = 8) -> list[str]:
    """Stream only the lines this query needs. Each source is an
    async callable (terms, limit) -> list[str]; results merge by
    score and the archive itself is never loaded whole."""
    key = f"{scope}:{query[:80]}"
    cached = _cache_get(key)
    if cached is not None:
        return cached.split("\n") if cached else []
    t = terms(query)
    if not t:
        return []
    hits: list[str] = []
    for src in sources:
        try:
            hits.extend(await src(t, limit))
        except Exception:
            continue  # a failing source degrades recall, never kills it
    out = hits[:limit]
    _cache_put(key, "\n".join(out))
    return out
