"""Validate every inline JavaScript block in the shipped UI."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parent
html = (root / "web" / "templates" / "index.html").read_text(encoding="utf-8")
scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.DOTALL | re.IGNORECASE)
node = shutil.which("node") or str(root / "bin" / "node.exe")
if not Path(node).is_file():
    raise SystemExit("Node.js not found")

failed = False
for index, source in enumerate(scripts):
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
        handle.write(source)
        temporary = Path(handle.name)
    try:
        result = subprocess.run([node, "--check", str(temporary)], capture_output=True, text=True)
    finally:
        temporary.unlink(missing_ok=True)
    if result.returncode:
        failed = True
        print(f"Script {index}: ERROR\n{result.stderr}")
    else:
        print(f"Script {index}: OK ({len(source)} chars)")

raise SystemExit(1 if failed else 0)
