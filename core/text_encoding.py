"""Evidence-based repair for mixed UTF-8/legacy-code-page mojibake."""
from __future__ import annotations

import re
from typing import Any

# These sequences are characteristic of UTF-8 decoded as a legacy single-byte codec.
_MARKERS = ("Ã", "Â", "Ä", "Ð", "Ñ", "áº", "á»", "â€", "â€™", "â€œ", "â€“", "â€¦", "�")
_TOKEN_RE = re.compile(r"\S+")
# UTF-8 decoded through cp1252 and then latin1 can mix characters from both
# byte mappings (e.g. á»‹: the final byte is cp1252's ‹).
_REVERSE_CP1252 = {bytes([byte]).decode("cp1252"): byte for byte in range(256)
                   if byte not in (0x81, 0x8d, 0x8f, 0x90, 0x9d)}
_REVERSE_CP1252.update({chr(byte): byte for byte in (0x81, 0x8d, 0x8f, 0x90, 0x9d)})
# File identities and links must continue to address the existing on-disk records.
_IDENTITY_KEYS = frozenset({"id", "job_id", "filename", "youtube_url", "url"})


def mojibake_marker_score(value: str) -> int:
    """Return a conservative count of known mojibake markers."""
    return sum(value.count(marker) for marker in _MARKERS)


def _codec_candidate(value: str, codec: str) -> str | None:
    try:
        if codec == "mixed":
            raw = bytes(_REVERSE_CP1252.get(char, ord(char)) for char in value)
        else:
            raw = value.encode(codec)
        return raw.decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError, ValueError):
        return None


def repair_mojibake_text(value: str) -> str:
    """Repair only evidence-backed spans, leaving clean Unicode unchanged."""
    if not isinstance(value, str) or mojibake_marker_score(value) == 0:
        return value

    best = value
    best_score = mojibake_marker_score(value)
    for codec in ("cp1252", "latin1", "mixed"):
        candidate = _codec_candidate(value, codec)
        if candidate is not None and mojibake_marker_score(candidate) < best_score:
            best, best_score = candidate, mojibake_marker_score(candidate)

    # Runtime records and large mixed source files can contain clean Vietnamese
    # beside damaged words, so also evaluate each whitespace-delimited span.
    def replace_token(match: re.Match[str]) -> str:
        token = match.group(0)
        token_score = mojibake_marker_score(token)
        if token_score == 0:
            return token
        chosen = token
        chosen_score = token_score
        for codec in ("cp1252", "latin1", "mixed"):
            candidate = _codec_candidate(token, codec)
            if candidate is not None and mojibake_marker_score(candidate) < chosen_score:
                chosen, chosen_score = candidate, mojibake_marker_score(candidate)
        return chosen

    token_candidate = _TOKEN_RE.sub(replace_token, value)
    if mojibake_marker_score(token_candidate) < best_score:
        best = token_candidate
    return best


def repair_mojibake(value: Any) -> Any:
    """Recursively repair strings while preserving container structure."""
    if isinstance(value, str):
        return repair_mojibake_text(value)
    if isinstance(value, dict):
        return {key: item if key in _IDENTITY_KEYS else repair_mojibake(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [repair_mojibake(item) for item in value]
    if isinstance(value, tuple):
        return tuple(repair_mojibake(item) for item in value)
    return value
