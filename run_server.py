import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, r"D:\Highlight_Video_Studio")
sys.path.insert(0, r"D:\Highlight_Video_Studio\web")

import waitress
from web.app import app

if __name__ == "__main__":
    print("Highlight Video Studio server starting on port 5080...")
    waitress.serve(app, host="0.0.0.0", port=5080, threads=8, channel_timeout=30)
