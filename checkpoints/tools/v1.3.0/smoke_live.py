"""Read-only checks of the installed v1.3.0 application; no Meta mutations."""
import hashlib
import json
import pathlib
import time
from datetime import datetime

import requests

SOURCE = pathlib.Path(__file__).resolve().parents[3]
ROOT = SOURCE.parent
TARGET = ROOT / "Highlight destop test"
EVIDENCE = SOURCE / "checkpoints/evidence/v1.3.0"
url = (TARGET / "run/desktop_url.txt").read_text().strip()
session = requests.Session()
session.trust_env = False


def read(endpoint):
    start = time.perf_counter()
    result = session.get(url + endpoint, timeout=30)
    result.raise_for_status()
    return result.json(), round((time.perf_counter() - start) * 1000, 2)


info, info_ms = read("/api/system/info")
queue, queue_ms = read("/api/queue/status")
scheduler, scheduler_ms = read("/api/scheduler/status")
identity = json.loads((TARGET / "build_identity.json").read_text(encoding="utf-8-sig"))
plans = json.loads((TARGET / "config/output_pipeline.json").read_text(encoding="utf-8-sig"))["plans"]
index = (TARGET / "web/index.html").read_bytes()
template = (TARGET / "web/templates/index.html").read_bytes()
assert info["app_version"] == identity["app_version"] == "1.3.0"
assert identity["source_commit"] == "f3b2b2b4aa90ed233862e326b536a2057f09b0a7"
assert index == template
assert b"recover-existing" in index
plan = next(p for p in plans if p["id"] == "group:grp_1791020096_3")
assert plan["posts_per_day"] == 2 and plan["slots"] == ["04:00", "10:50"]
assert len(plan["page_ids"]) == 100
timings = []
for bucket in ["all", "app", "published"]:
    data, elapsed = read("/api/posts/list?bucket=" + bucket + "&limit=20&offset=0")
    timings.append({"bucket": bucket, "response_ms": elapsed})
report = {
    "checked_at": datetime.now().astimezone().isoformat(),
    "success": True,
    "url": url,
    "app_version": info["app_version"],
    "source_commit": identity["source_commit"],
    "queue": {key: queue.get(key) for key in ["is_paused", "active", "running", "queued"]},
    "scheduler_cycle_active": scheduler.get("cycle_active"),
    "plan": {"id": plan["id"], "posts_per_day": plan["posts_per_day"], "slots": plan["slots"], "page_count": len(plan["page_ids"])},
    "templates_identical": True,
    "template_sha256": hashlib.sha256(index).hexdigest(),
    "http_ms": {"system_info": info_ms, "queue_status": queue_ms, "scheduler_status": scheduler_ms},
    "posts_list_timings": timings,
    "timing_scope": "Read-only local API responses on this running installation; not an end-to-end render benchmark",
}
EVIDENCE.mkdir(parents=True, exist_ok=True)
(EVIDENCE / "runtime_smoke.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report))
