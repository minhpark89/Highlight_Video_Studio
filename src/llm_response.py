"""Defensive parsing for OpenAI-compatible and 9router responses.

9router may return a normal JSON envelope for image generation but an SSE stream
(``data: {...}``) for chat completions even when the caller did not explicitly
request streaming.  Keep provider quirks out of feature code and never let a
valid streamed response become ``JSONDecodeError``.
"""
from __future__ import annotations

import json
import re
from typing import Any


def _json_candidates(text: str):
    text = str(text or "").strip()
    if not text:
        return
    # Markdown fences and optional reasoning wrappers are common with Claude.
    cleaned = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.I)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned).strip()
    for candidate in (cleaned, text):
        try:
            value = json.loads(candidate, strict=False)
            if isinstance(value, (dict, list)):
                yield value
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    # Extract the outermost object/array without requiring greedy malformed text.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start >= 0 and end > start:
            try:
                value = json.loads(cleaned[start:end + 1], strict=False)
                if isinstance(value, (dict, list)):
                    yield value
            except (TypeError, ValueError, json.JSONDecodeError):
                pass


def _content_from_chunk(chunk: Any) -> str:
    if not isinstance(chunk, dict):
        return ""
    # Some compatible gateways put the streamed text directly in the event
    # rather than under choices[].
    for direct_key in ("content", "text", "delta"):
        direct = chunk.get(direct_key)
        if isinstance(direct, str):
            return direct
        if isinstance(direct, dict) and isinstance(direct.get("content"), str):
            return direct["content"]
    choices = chunk.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return ""
    choice = choices[0]
    message = choice.get("message") or {}
    delta = choice.get("delta") or {}
    value = message.get("content") or delta.get("content") or choice.get("text")
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(value or "")


def chat_text_from_response(response) -> str:
    """Return assistant text from normal JSON, SSE, or mixed 9router output."""
    raw = getattr(response, "text", "") or ""
    # First handle a conventional JSON response (including fake responses in tests).
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        text = _content_from_chunk(payload)
        if text:
            return text.strip()
        # Some gateways wrap the completion in response/output/data.
        for key in ("response", "output", "data"):
            nested = payload.get(key)
            if isinstance(nested, dict):
                text = _content_from_chunk(nested)
                if text:
                    return text.strip()
            elif isinstance(nested, str) and nested.strip():
                return nested.strip()
    elif isinstance(payload, list):
        text = "".join(_content_from_chunk(item) for item in payload).strip()
        if text:
            return text

    chunks = []
    # If the body is not event-stream framed, preserve it verbatim. This keeps
    # markdown fences and prose-wrapped JSON intact for json_from_text instead
    # of accidentally discarding the JSON line while scanning SSE chunks.
    raw_text = str(raw)
    if "data:" not in raw_text:
        return raw_text.strip()
    # A few proxies return multiple SSE events without newlines. Split at the
    # event marker too, while retaining plain-text responses unchanged.
    if "\n" not in raw_text:
        raw_text = raw_text.replace("data:", "\ndata:").lstrip()
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith(":"):
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if line == "[DONE]":
            continue
        try:
            chunk = json.loads(line, strict=False)
        except (TypeError, ValueError, json.JSONDecodeError):
            # Preserve plain text providers too.
            if not chunks and line:
                chunks.append(line)
            continue
        text = _content_from_chunk(chunk)
        if text:
            chunks.append(text)
    text = "".join(chunks).strip()
    if text:
        return text
    # Last-resort plain body: this gives json_from_text a chance to parse a
    # markdown-wrapped JSON response from a non-conforming gateway.
    return raw_text.strip()


def json_from_text(text: str):
    """Parse JSON returned as plain text, fenced markdown, or prose-wrapped JSON."""
    for value in _json_candidates(text):
        return value
    raise ValueError("LLM response không chứa JSON hợp lệ")


def json_from_chat_response(response):
    return json_from_text(chat_text_from_response(response))
