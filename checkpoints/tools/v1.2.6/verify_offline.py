"""Record targeted offline tests and shipped JavaScript syntax; no live HTTP."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[3]
EVIDENCE = SOURCE / "checkpoints/evidence/v1.2.6"
TESTS = [
    "v126_content_recovery", "website_repair", "llm_response_parser", "content_studio_pipeline",
    "english_public_content", "video_recovery", "preview28_long_article_fallback",
    "preview28_image_provider_fallback", "preview23_image_sources", "preview26_source_metadata",
    "group_review", "post_retry", "meta_credential_recovery", "youtube_embed_publish",
    "website_ui_regression", "release_guards", "release_scheduler_fixes", "schedule_today",
    "schedule_media", "scheduling_publish_flow", "meta_queue_handoff", "meta_native_handoff",
    "meta_cancel", "installer_data_preservation", "first_comment_audit", "fallback_comments",
    "posting_schedule", "output_pipeline", "meta_scheduling_profiles", "parallel_publishing", "page_token_sync",
]

def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    args = [sys.executable, "-m", "pytest", *[f"tests/test_{name}.py" for name in TESTS],
            "-q", "--no-header", "--tb=short"]
    result = subprocess.run(args, cwd=SOURCE, capture_output=True, text=True, encoding="utf-8",
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    (EVIDENCE / "offline_tests.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    summary = next((line for line in reversed(result.stdout.splitlines()) if "passed" in line or "failed" in line), "")
    report = {"success": result.returncode == 0, "summary": summary, "test_files": TESTS,
              "live_http_disabled": True, "live_meta_write": False, "live_cms_write": False,
              "active_runtime_modified": False, "verified_at_utc": datetime.now(timezone.utc).isoformat()}
    (EVIDENCE / "offline_tests.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report), flush=True)
    if result.returncode:
        print(result.stdout[-16000:])
        return result.returncode
    node = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("node")
    count = 0
    with tempfile.TemporaryDirectory(prefix="hvs-v126-js-") as folder:
        for name in ("web/index.html", "web/templates/index.html"):
            source = (SOURCE / name).read_text(encoding="utf-8")
            for index, (attributes, code) in enumerate(re.findall(r"<script\b([^>]*)>(.*?)</script>", source, re.I | re.S)):
                if re.search(r"\bsrc\s*=", attributes, re.I) or not code.strip():
                    continue
                path = Path(folder) / f"inline-{count}-{index}.js"
                path.write_text(code, encoding="utf-8")
                check = subprocess.run([str(node), "--check", str(path)], capture_output=True,
                    text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if check.returncode:
                    raise RuntimeError(f"JavaScript syntax failed: {name}, script {index}: {check.stderr[:1000]}")
                count += 1
        check = subprocess.run([str(node), "--check", str(SOURCE / "web/full_script.js")], capture_output=True,
            text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if check.returncode:
            raise RuntimeError("JavaScript syntax failed: web/full_script.js")
    js = {"success": True, "inline_scripts_checked": count, "external_scripts_checked": 1,
          "templates_identical": (SOURCE / "web/index.html").read_bytes() == (SOURCE / "web/templates/index.html").read_bytes(),
          "browser_interaction_tested": False}
    (EVIDENCE / "javascript_syntax.json").write_text(json.dumps(js, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(js))
    return 0

if __name__ == "__main__":
    sys.exit(main())
