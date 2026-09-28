import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "web"))
os.chdir(str(ROOT_DIR))


def _prepare_local_hardware_profile():
    """Benchmark once before Flask imports its queue and render modules."""
    from multi_pc.profile_cache import build_or_load_profile

    bin_dir = ROOT_DIR / "bin"
    ffmpeg = str(bin_dir / "ffmpeg.exe") if (bin_dir / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe = str(bin_dir / "ffprobe.exe") if (bin_dir / "ffprobe.exe").exists() else "ffprobe"
    data_dir = ROOT_DIR / "data"
    temp_dir = ROOT_DIR / "temp" / "hardware_canary"
    data_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    entry = build_or_load_profile(
        data_dir / "hardware_profile.json",
        ffmpeg,
        ffprobe,
        temp_dir,
        force=os.environ.get("HIGHLIGHT_FORCE_HARDWARE_PROBE") == "1",
    )
    profile = entry.get("profile") or {}
    os.environ["HIGHLIGHT_ENCODER"] = str(profile.get("encoder") or "cpu")
    os.environ["HIGHLIGHT_MAX_CONCURRENT_RENDERS"] = str(max(1, int(profile.get("max_concurrent_renders") or 1)))
    return entry


HARDWARE_PROFILE = _prepare_local_hardware_profile()

import waitress
from web.app import app


if __name__ == "__main__":
    bind_host = "127.0.0.1"
    requested_host = os.environ.get("HIGHLIGHT_BIND_HOST", bind_host).strip()
    if requested_host not in ("127.0.0.1", "localhost", "::1"):
        print(f"Ignoring unsafe bind host {requested_host!r}; desktop server is loopback-only.")
    port = int(os.environ.get("HIGHLIGHT_PORT", "5080"))
    print(f"Highlight Video Studio starting on http://{bind_host}:{port}...")
    waitress.serve(app, host=bind_host, port=port, threads=8, channel_timeout=30)
