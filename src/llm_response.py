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

_MAX_TEXT = 1_000_000
_MAX_STARTS = 64


def _json_candidates(text: str):
    text = str(text or "").strip()
    if not text or len(text) > _MAX_TEXT:
        return
    # A reasoning prelude can contain incidental braces. Prefer the answer in
    # a JSON fence, then scan the visible reply after complete think blocks.
    visible = re.sub(r"<think\b[^>]*>.*?</think\s*>", "", text, flags=re.I | re.S)
    fences = re.findall(r"```(?:json)?[ \t]*\r?\n(.*?)```", visible, flags=re.I | re.S)
    decoder = json.JSONDecoder(strict=False)
    for candidate in (*fences, visible):
        candidate = candidate.strip()
        if not candidate:
            continue
        if candidate.startswith("```"):
            candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.I).strip()
        try:
            value = decoder.decode(candidate)
            if isinstance(value, (dict, list)):
                yield value
                continue
        except ValueError:
            pass
        # raw_decode finds one balanced JSON value despite trailing prose or
        # another fenced block; greedy first/last brace slicing cannot.
        starts = (match.start() for match in re.finditer(r"[\[{]", candidate))
        for index, start in enumerate(starts):
            if index >= _MAX_STARTS:
                break
            try:
                value, _ = decoder.raw_decode(candidate, start)
                if isinstance(value, (dict, list)):
                    yield value
                    break
            except ValueError:
                pass


def _content_from_chunk(chunk: Any) -> str:
    if not isinstance(chunk, dict):
        return ""
    # Some compatible gateways put the streamed text directly in the event
    # rather than under choices[].
    for direct_key in ("content", "output_text", "text", "delta"):
        direct = chunk.get(direct_key)
        if isinstance(direct, str):
            return direct
        if isinstance(direct, dict) and isinstance(direct.get("content"), str):
            return direct["content"]
        if isinstance(direct, dict) and isinstance(direct.get("text"), str):
            return direct["text"]
        if isinstance(direct, dict) and direct_key == "content":
            return json.dumps(direct, ensure_ascii=False)
        if isinstance(direct, list) and direct_key == "content":
            return "".join(_content_from_chunk(item) for item in direct if isinstance(item, dict))
    # OpenAI Responses-style envelopes carry output_text inside output items.
    output = chunk.get("output")
    if isinstance(output, list):
        return "".join(_content_from_chunk(item) for item in output if isinstance(item, dict))
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
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
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
            elif isinstance(nested, list):
                text = "".join(_content_from_chunk(item) for item in nested if isinstance(item, dict)).strip()
                if text:
                    return text
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
    if len(raw_text) > _MAX_TEXT:
        return ""
    if not re.search(r"(?:^|\n)\s*data:", raw_text):
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
        except ValueError:
            # Ignore SSE metadata/malformed events; never prepend them to a
            # valid stream of content chunks.
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


def chat_stream_incomplete(response) -> bool:
    """Detect a 200 SSE body that never completed a chat choice.

    Only inspect protocol metadata; never return or log provider body text.
    A completed SSE response has a non-null choice finish_reason, or a [DONE]
    marker. Empty or prematurely cut streams must not be retried as if they
    were a complete but badly formatted model answer.
    """
    raw = str(getattr(response, "text", "") or "")
    if not re.search(r"(?:^|\n)\s*data:", raw):
        return False
    if len(raw) > _MAX_TEXT:
        return True
    saw_choice = False
    for line in raw.splitlines():
        if not line.lstrip().startswith("data:"):
            continue
        value = line.lstrip()[5:].strip()
        if value == "[DONE]":
            return False
        try:
            event = json.loads(value)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        for choice in event.get("choices") or []:
            if isinstance(choice, dict):
                saw_choice = True
                if choice.get("finish_reason"):
                    return False
    return saw_choice
