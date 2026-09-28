"""Real render smoke test: use the cached hardware profile's chosen encoder, validate with ffprobe."""
import json
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

prof = json.loads((ROOT / "artifacts" / "hardware_profile.json").read_text(encoding="utf-8"))
profile = prof["profile"]
encoder = profile["encoder"]
codec = profile["codec"]
concurrency = profile["max_concurrent_renders"]
realtime = profile.get("canary", {}).get("realtime_factor")

print("chosen encoder :", encoder, "/", codec)
print("concurrency    :", concurrency)
print("profile canary :", realtime, "x realtime")

tmp = Path(tempfile.mkdtemp(prefix="hl_smoke_"))
src = tmp / "src.mp4"
out = tmp / "out.mp4"

gen = subprocess.run(
    ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=30:duration=6",
     "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(src)],
    capture_output=True, text=True,
)
print("source gen rc:", gen.returncode, "bytes:", src.stat().st_size if src.exists() else 0)

cmd = ["ffmpeg", "-y", "-ss", "1", "-t", "3", "-i", str(src)]
if codec == "h264_nvenc":
    cmd += ["-c:v", codec, "-preset", "p2", "-cq", "21"]
elif codec == "libx264":
    cmd += ["-c:v", codec, "-preset", "veryfast", "-crf", "21"]
elif codec == "h264_qsv":
    cmd += ["-c:v", codec, "-preset", "veryfast", "-global_quality", "21"]
else:
    cmd += ["-c:v", codec, "-quality", "speed"]
cmd += ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]

t0 = time.perf_counter()
r = subprocess.run(cmd, capture_output=True, text=True)
elapsed = time.perf_counter() - t0
print("render rc:", r.returncode)
if r.returncode != 0:
    print(r.stderr[-1200:])
    raise SystemExit(1)
print("render elapsed: %.3fs  realtime_factor: %.2fx (3s clip)" % (elapsed, 3.0 / elapsed))
print("output bytes:", out.stat().st_size)

probe = subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
     "-show_entries", "stream=codec_name,width,height,nb_read_frames,duration",
     "-of", "json", str(out)],
    capture_output=True, text=True,
)
info = json.loads(probe.stdout)["streams"][0]
print("ffprobe valid :", {k: info.get(k) for k in ("codec_name", "width", "height", "nb_read_frames")})
# ffprobe reports the container codec ("h264"), not the encoder implementation ("h264_nvenc").
expected_codec = "h264" if codec.startswith("h264") else codec
assert info["codec_name"] == expected_codec, info
assert info["width"] == 1920 and info["height"] == 1080, info
assert int(info["nb_read_frames"]) >= 80, info

result = {
    "encoder": encoder,
    "codec": codec,
    "concurrency": concurrency,
    "smoke_elapsed_seconds": round(elapsed, 3),
    "smoke_realtime_factor": round(3.0 / elapsed, 2),
    "output_bytes": out.stat().st_size,
    "ffprobe": {k: info.get(k) for k in ("codec_name", "width", "height", "nb_read_frames", "duration")},
    "profile_canary_realtime": realtime,
    "status": "PASS",
}
(ROOT / "artifacts" / "render_smoke_result.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8"
)
print("SMOKE TEST: PASS")
print("tmp dir:", tmp)
