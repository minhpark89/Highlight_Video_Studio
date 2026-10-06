"""Shared Meta API contract. See docs/META_V24_BACKEND.md for official sources."""

import re

GRAPH_API_VERSION = "v24.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

REEL_REQUIRED_PERMISSIONS = frozenset({
    "pages_show_list", "pages_read_engagement", "pages_manage_posts",
})
COMMENT_REQUIRED_PERMISSIONS = frozenset({
    "pages_show_list", "pages_read_user_content", "pages_manage_engagement",
})


def bearer_headers(token):
    """Graph accepts Bearer authentication; rupload uses OAuth instead."""
    return {"Authorization": f"Bearer {str(token or '').strip()}"}


def safe_meta_text(value, token="", limit=600):
    text = str(value or "")
    if token:
        text = text.replace(str(token), "[redacted]")
    text = re.sub(r"\b(?:Bearer|OAuth)\s+[^\s\"',]+", "[redacted]", text, flags=re.I)
    text = re.sub(r"\b(?:access_token|page_token|appsecret_proof|client_secret)\s*[=:]\s*[^\s&\"',]+",
                  "[redacted]", text, flags=re.I)
    text = re.sub(r"\bEA[A-Za-z0-9_-]{20,}\b", "[redacted]", text)
    return " ".join(text.split())[:limit]


def graph_error_message(data, token="", http_status=None):
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        return safe_meta_text(f"[{error.get('code', http_status)}] {error.get('message') or 'Meta rejected the request'}", token)
    return f"Meta response could not be verified (HTTP {http_status or 'unknown'})."
