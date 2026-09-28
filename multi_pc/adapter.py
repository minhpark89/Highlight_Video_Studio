from collections.abc import Callable
from pathlib import Path
from typing import Any

from .security import redact


class AdapterError(RuntimeError):
    """A safe, reportable local adapter failure."""


class SafeLocalAdapter:
    """Dispatch only explicitly registered Python callables; never shell commands."""

    ALLOWED_ACTIONS = frozenset({"highlight_pipeline", "publish_zernio"})

    def __init__(self, handlers: dict[str, Callable] | None = None):
        self._handlers: dict[str, Callable] = {}
        for action, handler in (handlers or {}).items():
            self.register(action, handler)

    def register(self, action: str, handler: Callable) -> None:
        if action not in self.ALLOWED_ACTIONS:
            raise AdapterError(f"action is not allowlisted: {action}")
        if not callable(handler):
            raise AdapterError("handler must be callable")
        self._handlers[action] = handler

    def execute(self, action: str, payload: dict[str, Any], progress: Callable[[dict], None]) -> dict:
        if action not in self.ALLOWED_ACTIONS:
            raise AdapterError(f"action is not allowlisted: {action}")
        handler = self._handlers.get(action)
        if handler is None:
            raise AdapterError(f"local handler is not configured: {action}")
        # Handlers receive structured data only. This layer intentionally has no
        # subprocess, eval, exec, shell, command, or arbitrary import interface.
        result = handler(dict(payload), lambda update: progress(redact(update)))
        if not isinstance(result, dict):
            raise AdapterError("handler result must be an object")
        return redact(result)


def local_artifact_result(path: str | Path, **metadata) -> dict:
    artifact = Path(path).expanduser().resolve()
    if not artifact.is_file():
        raise AdapterError("local output artifact does not exist")
    # Only a local reference and small metadata are returned. File bytes do not
    # cross the control plane in Phase 1.
    return {"local_output_ref": str(artifact), "bytes": artifact.stat().st_size, **metadata}
