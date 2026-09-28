"""Canonical writable-data root and cross-process single-instance helpers."""
from __future__ import annotations

import os
import socket
import time
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent


def canonical_data_root(*, allow_repo_fallback=None) -> Path:
    """Return the one canonical root for mutable app state on this installation.

    ``HIGHLIGHT_DATA_ROOT`` wins when set. Otherwise the installation root that owns
    this module wins, which keeps a packaged app and a dev checkout from writing two
    different queues. ``allow_repo_fallback`` lets a caller pass the repo root it
    resolved so mismatched installs fail loudly instead of silently forking state.
    """
    configured = str(os.environ.get("HIGHLIGHT_DATA_ROOT") or "").strip()
    fallback = Path(allow_repo_fallback).resolve() if allow_repo_fallback else APP_ROOT
    if configured:
        root = Path(configured).expanduser().resolve()
        if allow_repo_fallback and root != fallback:
            raise RuntimeError(
                f"HIGHLIGHT_DATA_ROOT ({root}) does not match this installation ({fallback})"
            )
    else:
        root = fallback
    root.mkdir(parents=True, exist_ok=True)
    return root


class ProcessLease:
    """Atomic directory lease used to prevent duplicate workers across processes."""

    def __init__(self, name: str, root: Path | None = None, stale_after: int = 180):
        self.root = (root or canonical_data_root()) / "run"
        self.path = self.root / f"{name}.lease"
        self.owner_file = self.path / "owner"
        self.stale_after = max(30, int(stale_after))
        self.acquired = False

    def acquire(self) -> bool:
        self.root.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                self.path.mkdir()
                self.owner_file.write_text(
                    f"pid={os.getpid()}\nhost={socket.gethostname()}\nstarted={int(time.time())}\n",
                    encoding="utf-8",
                )
                self.acquired = True
                return True
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                    if age <= self.stale_after:
                        return False
                    for child in self.path.iterdir():
                        child.unlink(missing_ok=True)
                    self.path.rmdir()
                except OSError:
                    return False
        return False

    def touch(self) -> None:
        if self.acquired:
            try:
                self.owner_file.touch()
                os.utime(self.path, None)
            except OSError:
                pass

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            self.owner_file.unlink(missing_ok=True)
            self.path.rmdir()
        except OSError:
            pass
        self.acquired = False
