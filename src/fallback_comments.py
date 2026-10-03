"""Stable, factual First Comment lead-ins for a verified article URL."""
from __future__ import annotations

import hashlib
from urllib.parse import urlsplit


LEAD_INS = (
    "See the full video and context in the article:",
    "Want the complete recording? Open the article:",
    "The source video and viewing notes are here:",
    "Watch the original footage with the article:",
    "Read the context and play the full video here:",
    "The complete video is available in this article:",
    "Take a closer look at the source footage:",
    "For the full recording and context, visit:",
    "See the longer video alongside our notes:",
    "Open the article to review the original video:",
    "Watch beyond the short clip in this article:",
    "The full video and article are available here:",
    "Review the complete sequence at the source:",
    "See the original recording before drawing a conclusion:",
    "Find the full video and a short viewing guide here:",
    "Explore the source video and its context:",
    "Open this article for the longer recording:",
    "The article includes the full video for a closer look:",
    "See more of the original footage here:",
    "Read the article and watch the full recording:",
    "The full source video is embedded in the article:",
    "Need more context than the short clip? Start here:",
    "Follow the full sequence in the original video:",
    "Watch the complete footage in the article:",
    "See what the original video shows in full:",
    "Open the full video and accompanying notes:",
    "The article brings together the source video and context:",
    "Take another look with the complete recording:",
    "Read the viewing guide and play the source video:",
    "Find the original footage in this article:",
)


def fallback_first_comment(title: str, article_url: str) -> str:
    url = str(article_url or "").strip()
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
        return ""
    key = f"{title}\n{url}".encode("utf-8")
    index = int.from_bytes(hashlib.sha256(key).digest()[:8], "big") % len(LEAD_INS)
    return f"{LEAD_INS[index]} {url}"
