"""Loopback-only local launcher for Highlight Video Studio.

Starts the existing Flask backend on an isolated loopback port with a per-run session token,
so the desktop shell can talk to it without Basic Auth, a public port, a router change, or any
reverse tunnel. Production v1.0.19 on port 5080 is never touched by this module.

Design rules:
- Bind ``127.0.0.1`` only. Never ``0.0.0.0``, never a public interface.
- Pick an ephemeral/random free port unless one is pinned explicitly for the shell.
- Gate every request with a session token sent as ``X-Highlight-Session`` or a cookie.
- Allow only loopback client addresses; refuse anything else.
- Write the port + token to a per-user runtime file so the shell can attach, then delete it on exit.
"""

from __future__ import annotations

import json
import os
import secrets
import socket
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .security import canonical_json

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
SESSION_HEADER = "X-Highlight-Session"
SESSION_COOKIE = "highlight_session"
DEFAULT_RUNTIME_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "HighlightVideoStudio" / "run"
EXEMPT_PATHS = ("/healthz",)
TOKEN_BYTES = 32


class LoopbackBindError(RuntimeError):
    """Raised when a non-loopback bind host is requested."""


@dataclass
class RuntimeHandle:
    host: str
    port: int
    token: str
    pid: int
    started_at: str
    runtime_file: Path | None = None
    url: str = field(init=False)

    def __post_init__(self) -> None:
        self.url = f"http://{self.host}:{self.port}"

    def public_dict(self, include_token: bool = False) -> dict:
        data = {
            "host": self.host,
            "port": self.port,
            "pid": self.pid,
            "started_at": self.started_at,
            "url": self.url,
        }
        if include_token:
            data["token"] = self.token
        return data

    def write_runtime_file(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path else self.runtime_file
        if target is None:
            raise ValueError("runtime file path required")
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".tmp")
        temp.write_text(canonical_json(self.public_dict(include_token=True)), encoding="utf-8")
        temp.replace(target)
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
        self.runtime_file = target
        return target

    def remove_runtime_file(self) -> None:
        if self.runtime_file:
            try:
                Path(self.runtime_file).unlink()
            except OSError:
                pass


def assert_loopback(host: str) -> str:
    normalized = (host or "").strip().lower()
    if normalized not in LOOPBACK_HOSTS:
        raise LoopbackBindError(
            f"Refusing to bind non-loopback host {host!r}; Highlight must stay local-only."
        )
    return normalized


def pick_free_port(host: str = "127.0.0.1") -> int:
    """Ask the OS for an unused ephemeral port on the loopback interface."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((assert_loopback(host), 0))
        return int(sock.getsockname()[1])


def new_session_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def _is_loopback_client(address: str) -> bool:
    if not address:
        return False
    candidate = address.strip()
    if candidate in LOOPBACK_HOSTS:
        return True
    if candidate.startswith("::ffff:"):
        candidate = candidate[7:]
    parts = candidate.split(".")
    if len(parts) == 4 and all(part.isdigit() for part in parts):
        return parts[0] == "127"
    return candidate == "::1"


class SessionGuard:
    """Constant-time session check limited to loopback clients."""

    def __init__(self, token: str):
        if not token:
            raise ValueError("session token required")
        self._token_bytes = token.encode("utf-8")

    def extract(self, environ: dict) -> str:
        header = environ.get("HTTP_X_HIGHLIGHT_SESSION", "")
        if header:
            return header
        cookie = environ.get("HTTP_COOKIE", "")
        for part in cookie.split(";"):
            name, _, value = part.strip().partition("=")
            if name == SESSION_COOKIE:
                return value
        return ""

    def authorize(self, environ: dict) -> bool:
        if not _is_loopback_client(environ.get("REMOTE_ADDR", "")):
            return False
        path = environ.get("PATH_INFO", "")
        if path in EXEMPT_PATHS:
            return True
        supplied = self.extract(environ)
        if not supplied:
            return False
        return secrets.compare_digest(supplied.encode("utf-8"), self._token_bytes)

    def wsgi_middleware(self, app):
        def wrapped(environ, start_response):
            if not self.authorize(environ):
                body = b"unauthorized"
                start_response(
                    "401 Unauthorized",
                    [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))],
                )
                return [body]
            return app(environ, start_response)

        return wrapped


def resolve_config(host: str | None = None, port: int | None = None, runtime_dir: str | Path | None = None) -> dict:
    resolved_host = assert_loopback(host or os.environ.get("HIGHLIGHT_BIND_HOST", "127.0.0.1") or "127.0.0.1")
    pinned = port if port is not None else os.environ.get("HIGHLIGHT_LOCAL_PORT")
    resolved_port = int(pinned) if pinned else pick_free_port(resolved_host)
    if resolved_port == 5080:
        raise LoopbackBindError("Port 5080 belongs to the running production app; refusing to reuse it.")
    directory = Path(runtime_dir) if runtime_dir else DEFAULT_RUNTIME_DIR
    return {"host": resolved_host, "port": resolved_port, "runtime_dir": directory}


def build_handle(config: dict, token: str | None = None) -> RuntimeHandle:
    return RuntimeHandle(
        host=config["host"],
        port=int(config["port"]),
        token=token or new_session_token(),
        pid=os.getpid(),
        started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        runtime_file=Path(config["runtime_dir"]) / "runtime.json",
    )


def build_app(root_dir: str | Path | None = None, handle: RuntimeHandle | None = None):
    """Build the existing Flask app and wrap it in the loopback session guard."""
    import importlib
    import sys

    root = Path(root_dir or Path(__file__).resolve().parent.parent).resolve()
    for candidate in (str(root), str(root / "web")):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)
    previous = Path.cwd()
    try:
        os.chdir(str(root))
        module = importlib.import_module("web.app")
        flask_app = getattr(module, "app")
    finally:
        os.chdir(str(previous))
    guard = SessionGuard(handle.token if handle else new_session_token())
    return guard.wsgi_middleware(flask_app), guard


def serve(host: str | None = None, port: int | None = None, runtime_dir: str | Path | None = None,
          root_dir: str | Path | None = None) -> RuntimeHandle:
    config = resolve_config(host=host, port=port, runtime_dir=runtime_dir)
    handle = build_handle(config)
    app, _guard = build_app(root_dir=root_dir, handle=handle)
    handle.write_runtime_file()

    try:
        import waitress
    except ImportError as exc:  # pragma: no cover - packaging must bundle waitress
        handle.remove_runtime_file()
        raise RuntimeError("waitress is required for the local launcher") from exc

    server = threading.Thread(
        target=waitress.serve,
        kwargs={
            "app": app,
            "host": handle.host,
            "port": handle.port,
            "threads": 8,
            "channel_timeout": 30,
        },
        daemon=True,
    )
    server.start()
    return handle


def run_forever(host: str | None = None, port: int | None = None,
                runtime_dir: str | Path | None = None, root_dir: str | Path | None = None) -> None:
    handle = serve(host=host, port=port, runtime_dir=runtime_dir, root_dir=root_dir)
    print(f"Highlight local runtime: {handle.url} (loopback only, session-gated)")
    print(f"Runtime file: {handle.runtime_file}")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        handle.remove_runtime_file()


def load_runtime_file(path: str | Path | None = None) -> dict | None:
    target = Path(path) if path else DEFAULT_RUNTIME_DIR / "runtime.json"
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


if __name__ == "__main__":  # pragma: no cover - manual run
    run_forever()
