"""Upload rendered HTML to a public file host so the brief gets a real URL.

We use catbox.moe by default — anonymous, permanent, no auth required, and
serves .html files with the correct text/html content-type so links render
directly in the browser. Falls back to 0x0.st if catbox is down.
"""

from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)


def _post_catbox(html: str, filename: str, timeout: float) -> str | None:
    try:
        resp = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (filename, html.encode("utf-8"), "text/html")},
            timeout=timeout,
        )
        resp.raise_for_status()
        url = resp.text.strip()
        if url.startswith("http") and "catbox.moe" in url:
            return url
        log.warning("Unexpected catbox response: %r", url[:200])
    except Exception as exc:
        log.warning("Catbox upload failed: %s", exc)
    return None


def _post_0x0st(html: str, filename: str, timeout: float) -> str | None:
    try:
        resp = requests.post(
            "https://0x0.st",
            files={"file": (filename, html.encode("utf-8"), "text/html")},
            data={"expires": "168"},  # 7 days
            timeout=timeout,
            headers={"User-Agent": "ContentIntelligence/1.0 (briefs upload)"},
        )
        resp.raise_for_status()
        url = resp.text.strip()
        if url.startswith("http"):
            return url
        log.warning("Unexpected 0x0.st response: %r", url[:200])
    except Exception as exc:
        log.warning("0x0.st upload failed: %s", exc)
    return None


def upload_html(html: str, filename: str = "indian-founder-briefs.html", timeout: float = 15.0) -> str | None:
    """Upload HTML to a public host and return a shareable URL.

    Tries catbox.moe (permanent, preferred) then 0x0.st (7-day TTL fallback).
    Returns None if both fail — caller should fall back to inline rendering.
    """
    return _post_catbox(html, filename, timeout) or _post_0x0st(html, filename, timeout)
