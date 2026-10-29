"""Skill forge — yesterday's logs become tomorrow's craft.

The loop: operational lessons accumulate in memory → past a
threshold, an agent distills them into a reusable skill document →
the skill's Digest travels in every future prompt. The forge runs
strict rails: quota per day, budget check, forbidden-pattern
rejection — a failed forge writes NOTHING, it never fakes a skill.

The brain call is injected: `propose(system, user)` must return the
drafted markdown or None. Everything else is deterministic.
"""
import re
import unicodedata
from pathlib import Path

MAX_DOC = 12000
MAX_CONCEPT = 400
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
FORBIDDEN = re.compile(
    r"https?://|sk-[a-zA-Z0-9]|bearer\s|<script|`", re.I)
DIGEST_RE = re.compile(r"## Digest\s*\n+(.*?)(?:\n---|\n## |\Z)", re.S)


class ForgeError(Exception):
    """Honest refusal — the caller surfaces this, never a fake."""


def slugify(text: str) -> str:
    flat = "".join(c for c in unicodedata.normalize("NFKD",
                                                    text.lower())
                   if not unicodedata.combining(c))
    return "-".join(re.findall(r"[a-z0-9]+", flat))[:40].strip("-")


def extract_digest(doc: str) -> str:
    m = DIGEST_RE.search(doc or "")
    return m.group(1).strip() if m else ""


async def forge(concept: str, slug: str, root: Path, propose,
                *, daily_used: int = 0, daily_max: int = 2) -> dict:
    """Draft a skill doc via the injected brain and persist it.

    Refuses honestly (ForgeError) on bad input, quota, brain
    failure, or output that breaks the rails — the atomic rename
    means readers never see half a skill."""
    concept = (concept or "").strip()
    if not (8 <= len(concept) <= MAX_CONCEPT):
        raise ForgeError("concept must be 8-400 chars")
    if FORBIDDEN.search(concept):
        raise ForgeError("concept rejected")
    if not SLUG_RE.match(slug):
        raise ForgeError("bad slug")
    if daily_used >= daily_max:
        raise ForgeError("daily forge quota reached")

    path = root / f"{slug}.md"
    if path.exists():
        raise ForgeError("skill already exists")

    system = (
        "You write a skill document — craft knowledge, dense and "
        "usable. Format, exactly:\n"
        "# <Title>\n\n<one short paragraph: what this craft is and "
        "when it applies>\n\n## Digest\n\n<max 120 words — the craft "
        "compressed into numbered imperative rules>\n\n---\n\n"
        "## <section>\n\n<3-6 sections: method, examples, and the "
        "ways this craft fails>\n\nRules: markdown only, no URLs, no "
        "code, no invented credentials — knowledge, not commands.")
    doc = await propose(system, f"Concept:\n{concept}")
    if not doc:
        raise ForgeError("the brain returned nothing")
    doc = doc.strip()
    if len(doc) > MAX_DOC or FORBIDDEN.search(doc):
        raise ForgeError("draft rejected by rails")
    digest = extract_digest(doc)
    if len(digest) < 40 or not doc.startswith("#"):
        raise ForgeError("draft lacks a usable Digest")

    root.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(doc)
    tmp.rename(path)  # atomic — readers never see half a skill
    return {"slug": slug, "title": doc.splitlines()[0].lstrip("#")
            .strip()[:120], "digest": digest}
