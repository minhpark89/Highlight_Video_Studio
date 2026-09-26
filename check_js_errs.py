import subprocess
import urllib.request
import re

url = "http://127.0.0.1:5080/"
try:
    resp = urllib.request.urlopen(url, timeout=5)
    html = resp.read().decode('utf-8', errors='replace')
    scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
    print("Found scripts:", len(scripts))
    for i, s in enumerate(scripts):
        with open(f"/tmp/test_s_{i}.js", "w", encoding="utf-8") as f:
            f.write(s)
        r = subprocess.run(["node", "--check", f"/tmp/test_s_{i}.js"], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"SCRIPT {i} SYNTAX ERROR:\n", r.stderr)
        else:
            print(f"SCRIPT {i} OK ({len(s)} chars)")
except Exception as e:
    print("Error:", e)
