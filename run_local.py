"""Standalone launcher for the Highlight Video Studio offline preview build.

Starts the existing Flask UI/backend on an ephemeral loopback port with a per-run session token.
No tunnel, no public port, no Basic Auth, no cloud dependency. The production app on port 5080 is
never started, stopped, or bound by this script.
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
for candidate in (str(ROOT_DIR), str(ROOT_DIR / "web")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)
os.chdir(str(ROOT_DIR))

from multi_pc.local_launcher import load_runtime_file, run_forever, serve  # noqa: E402

BANNER = "Highlight Video Studio — Offline Preview"


def _open_browser_later(url: str, token: str, delay: float = 2.5) -> None:
    def worker():
        import time

        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()


def main() -> int:
    if os.environ.get("HIGHLIGHT_PREVIEW_OPEN_BROWSER", "1") != "0":
        print(f"{BANNER}: starting on loopback only.")
    handle = serve()
    print(f"{BANNER}")
    print(f"  URL      : {handle.url}")
    print(f"  Session  : {handle.token}")
    print(f"  Runtime  : {handle.runtime_file}")
    print("  Note     : key is auto-attached in-browser; no public port is opened.")
    return handle


def main_blocking() -> None:
    existing = load_runtime_file()
    if existing and existing.get("port"):
        print(f"{BANNER}: existing runtime on port {existing['port']} (continuing anyway).")
    run_forever()


if __name__ == "__main__":
    run_forever()
