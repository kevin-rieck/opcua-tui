from __future__ import annotations

from urllib.parse import SplitResult, urlsplit, urlunsplit


def sanitize_endpoint(endpoint: str) -> str:
    value = endpoint.strip()
    if not value:
        return value

    try:
        parsed = urlsplit(value)
    except Exception:
        return value

    if "@" not in parsed.netloc:
        return value

    _userinfo, host_port = parsed.netloc.rsplit("@", 1)
    redacted = SplitResult(
        scheme=parsed.scheme,
        netloc=f"***@{host_port}",
        path=parsed.path,
        query=parsed.query,
        fragment=parsed.fragment,
    )
    return urlunsplit(redacted)
