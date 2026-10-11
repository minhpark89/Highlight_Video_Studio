"""Two fresh processes and a real render in a throwaway installation copy."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "build" / ("v132-restart-" + uuid.uuid4().hex)
WORK.mkdir(parents=True)
for name in ("core", "src", "web", "multi_pc", "research"):
    shutil.copytree(ROOT / name, WORK / name,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.bak", "*.bak*"))
for name in ("data", "output", "temp", "assets"):
    (WORK / name).mkdir()
shutil.copyfile(ROOT / "assets" / "highlight.ico", WORK / "assets" / "highlight.ico")
for name, value in (("config.json",{}), ("jobs.json",[]), ("posts.json",[])):
    (WORK / name).write_text(json.dumps(value), encoding="utf-8")
(WORK / "data" / "render_queue_state.json").write_text(json.dumps({
    "concurrency_mode":"manual", "manual_concurrency":4, "is_paused":True}), encoding="utf-8")
env = dict(os.environ)
env["HIGHLIGHT_DATA_ROOT"] = env["PYTHONPATH"] = str(WORK)
env["HIGHLIGHT_MAX_CONCURRENT_RENDERS"] = "2"
env["PATH"] = str(ROOT.parent / "Highlight destop test" / "bin") + os.pathsep + env["PATH"]
source = ROOT / "build" / "v132-benchmark" / "source.mp4"
code = """
import json, sys
from pathlib import Path
from web import app
from src import pipeline
from src.render_quality import validate_render
client = app.app.test_client()
state = client.get('/api/queue/status').json
assert state['concurrency_mode'] == 'manual'
assert state['max_concurrent'] == pipeline.RENDER_LIMITER.limit == 4
assert state['is_paused'] is True
assert client.get('/favicon.ico').status_code == 200
pipeline.config['video_pipeline'] = {'encoder':'cpu', 'crf':21}
output = pipeline.render_highlight_clip(source_video=sys.argv[1], start_time=0,
    end_time=6, output_path=str(Path('output') / 'restart-smoke.mp4'), subtitle_style='none')
quality = validate_render(output,6)
assert quality['fps'] == 30 and quality['quality_verified']
print('V132_RESTART_PROOF ' + json.dumps({'queue_limit':state['max_concurrent'],
    'render_limit':pipeline.RENDER_LIMITER.limit, 'paused':state['is_paused'],
    'render_duration':quality['duration'], 'fps':quality['fps'], 'full_decode_validated':True}))
"""
results = []
for _ in range(2):
    result = subprocess.run([sys.executable,"-c",code,str(source)], cwd=WORK, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    if result.returncode:
        raise RuntimeError(result.stdout[-1000:] + result.stderr[-2000:])
    line = next(line for line in result.stdout.splitlines() if line.startswith("V132_RESTART_PROOF "))
    results.append(json.loads(line.split(" ",1)[1]))
report = {"success":True, "fresh_processes":results,
          "scope":"isolated installation copy with actual app startup and actual FFmpeg render"}
(ROOT / "checkpoints" / "evidence" / "v1.3.2" / "restart_smoke.json").write_text(
    json.dumps(report,indent=2), encoding="utf-8")
print(json.dumps(report,indent=2))
