"""Secret-free diagnostics for the configured text chat route (not image generation)."""
from urllib.parse import urlsplit, urlunsplit


def chat_endpoint(base):
    parts = urlsplit(str(base or "").strip())
    if parts.scheme not in ("http", "https") or not parts.netloc or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("Text LLM api_base must be an http(s) base URL without credentials or query")
    path = parts.path.rstrip("/")
    if path.endswith("/chat/completions"):
        path = path[:-len("/chat/completions")]
    if not path.endswith("/v1"):
        path += "/v1"
    return urlunsplit((parts.scheme, parts.netloc, path + "/chat/completions", "", ""))


def chat_failure(status, *, has_key, has_model):
    if not has_model:
        return "Text LLM model missing: configure llm.model or llm.task_models for this task"
    if not has_key:
        return "Text LLM credential missing: configure llm.api_key for the text route"
    if status in (401, 403):
        return f"Text LLM HTTP {status}: credential rejected for configured text route; verify llm.api_base, llm.api_key and model authorization (image credentials do not prove text access)"
    if status in (404, 405):
        return f"Text LLM HTTP {status}: verify llm.api_base chat endpoint and selected model route"
    if status == 400:
        return "Text LLM HTTP 400: verify selected text model and request compatibility"
    return f"Text LLM HTTP {status}: chat request failed"
