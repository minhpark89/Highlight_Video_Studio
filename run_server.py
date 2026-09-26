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
    print("Highlight Video Studio starting on http://localhost:5080...")
    waitress.serve(app, host="0.0.0.0", port=5080, threads=8, channel_timeout=30)
