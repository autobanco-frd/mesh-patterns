"""Anti-SSRF — every outbound target must be a public URL.

An agent that fetches arbitrary URLs is an SSRF cannon aimed at its
own network. The rules that keep it harmless:

- scheme is http/https only (file://, gopher://, ftp:// die here)
- literal IPs are checked directly against is_global
- hostnames are RESOLVED and EVERY answer must be public — a name
  that resolves even once to a private IP is a DNS-rebinding vector
- negative results cache briefly; resolution failure is a closed
  door, never an open one

Stdlib only.
"""
import ipaddress
import socket
import time
from urllib.parse import urlparse

_DNS_CACHE: dict[str, tuple[float, bool]] = {}
_DNS_CACHE_TTL = 300.0


def _host_resolves_public(host: str) -> bool:
    now = time.monotonic()
    hit = _DNS_CACHE.get(host)
    if hit and now - hit[0] < _DNS_CACHE_TTL:
        return hit[1]
    ok = False
    try:
        infos = socket.getaddrinfo(host, None)
        addrs = {i[4][0] for i in infos}
        ok = bool(addrs) and all(
            ipaddress.ip_address(a).is_global for a in addrs)
    except (socket.gaierror, ValueError, OSError):
        ok = False
    _DNS_CACHE[host] = (now, ok)
    return ok


def is_public_url(url: str) -> bool:
    """True only for http(s) URLs whose host is verifiably public."""
    try:
        p = urlparse(url)
    except Exception:
        return False
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    host = p.hostname.lower()
    if host == "localhost":
        return False
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_global
    except ValueError:
        pass  # hostname — resolve before trusting
    return _host_resolves_public(host)
