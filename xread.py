"""Free X/Twitter reader — syndication CDN, no auth, no credits.

Reads single tweets via the public embed endpoint. For discovery,
pair with a web search (site:x.com) then read each id here.
Stdlib only.
"""
import json
import re
import urllib.request

_UA = {"User-Agent": "Mozilla/5.0 (compatible; mesh-patterns/1.0)"}
_TIMEOUT = 12


def _tweet_id(url_or_id: str) -> str | None:
    m = re.search(r"status/(\d+)|^(\d+)$", url_or_id.strip())
    return (m.group(1) or m.group(2)) if m else None


def read_tweet(url_or_id: str) -> dict:
    """Fetch a tweet via the public syndication CDN — free, no key."""
    tid = _tweet_id(url_or_id)
    if not tid:
        return {"ok": False, "error": "no tweet id in input"}
    url = (f"https://cdn.syndication.twimg.com/tweet-result"
           f"?id={tid}&lang=en&token=a")
    try:
        req = urllib.request.Request(url, headers=_UA)
        d = json.loads(urllib.request.urlopen(
            req, timeout=_TIMEOUT).read())
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}
    user = d.get("user") or {}
    return {
        "ok": True, "id": tid,
        "author": user.get("screen_name"),
        "author_name": user.get("name"),
        "text": d.get("text") or "",
        "created_at": d.get("created_at"),
        "likes": d.get("favorite_count"),
        "retweets": d.get("retweet_count"),
        "replies": d.get("conversation_count"),
        "media": [m.get("url") for m in
                  (d.get("mediaDetails") or [])][:4],
        "quoted": (d.get("quoted_tweet") or {}).get("text"),
    }


def read_thread(url_or_id: str) -> dict:
    """Tweet + parent chain if it's a reply."""
    out = read_tweet(url_or_id)
    if not out.get("ok"):
        return out
    tid = _tweet_id(url_or_id)
    try:
        url = (f"https://cdn.syndication.twimg.com/tweet-result"
               f"?id={tid}&lang=en&token=a")
        d = json.loads(urllib.request.urlopen(
            urllib.request.Request(url, headers=_UA),
            timeout=_TIMEOUT).read())
        parent = d.get("parent")
        if parent:
            p = read_tweet(str(parent.get("id_str", "")))
            out["parent"] = p
    except Exception:
        pass
    return out


if __name__ == "__main__":
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    print(json.dumps(read_thread(arg), ensure_ascii=False, indent=1))
