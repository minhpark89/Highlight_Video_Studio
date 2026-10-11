"""Record full offline tests and syntax checks for the shipped JavaScript."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "checkpoints/evidence/v1.3.2"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    tools = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "bin"
    env["PATH"] = str(tools) + os.pathsep + env.get("PATH", "")
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short"],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=NO_WINDOW)
    (EVIDENCE / "offline_tests.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    summary = next((line for line in reversed(result.stdout.splitlines()) if "passed" in line or "failed" in line), "")
    tests = {"success": result.returncode == 0, "summary": summary, "full_suite": True,
        "live_http_disabled": True, "live_meta_write": False, "live_cms_write": False,
        "active_runtime_modified": False, "verified_at_utc": datetime.now(timezone.utc).isoformat()}
    (EVIDENCE / "offline_tests.json").write_text(json.dumps(tests, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(tests), flush=True)
    if result.returncode:
        print(result.stdout[-12000:])
        return result.returncode
    node = shutil.which("node", path=env["PATH"])
    checked = []
    for name in [str(path.relative_to(ROOT)) for path in (ROOT / "web/static").glob("*.js")] + ["web/full_script.js"]:
        subprocess.run([node, "--check", str(ROOT / name)], check=True, capture_output=True, creationflags=NO_WINDOW)
        checked.append(name)
    inline = 0
    with tempfile.TemporaryDirectory(prefix="hvs-v132-js-") as temporary:
        for name in ("web/index.html", "web/templates/index.html"):
            source = (ROOT / name).read_text(encoding="utf-8")
            for index, (attributes, code) in enumerate(re.findall(r"<script\b([^>]*)>(.*?)</script>", source, re.I | re.S)):
                if re.search(r"\bsrc\s*=", attributes, re.I) or not code.strip():
                    continue
                target = Path(temporary) / f"inline-{inline}-{index}.js"
                target.write_text(code, encoding="utf-8")
                syntax = subprocess.run([node, "--check", str(target)], capture_output=True,
                    text=True, encoding="utf-8", creationflags=NO_WINDOW)
                if syntax.returncode:
                    raise RuntimeError(f"{name}, script {index}: {syntax.stderr}")
                inline += 1
    assert (ROOT / "web/index.html").read_bytes() == (ROOT / "web/templates/index.html").read_bytes()
    javascript = {"success": True, "inline_scripts_checked": inline,
        "external_scripts_checked": checked, "templates_identical": True}
    (EVIDENCE / "javascript_syntax.json").write_text(json.dumps(javascript, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(javascript))
    return 0


if __name__ == "__main__":
    sys.exit(main())
