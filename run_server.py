import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "web"))
os.chdir(str(ROOT_DIR))

import waitress
from web.app import app

if __name__ == "__main__":
    bind_host = os.environ.get("HIGHLIGHT_BIND_HOST", "127.0.0.1").strip() or "127.0.0.1"
    print(f"Highlight Video Studio starting on http://{bind_host}:5080...")
    waitress.serve(app, host=bind_host, port=5080, threads=8, channel_timeout=30)
