"""Pre-release local environment diagnostics and installation planning.

Offline by design: no cloud, no network calls, no binding of any public port. Produces a JSON
report (hardware, verified encoder, render profile, production-safety findings) and a plan-only
install layout that never writes into the running production install.
"""

from __future__ import annotations

import json
import platform
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .hardware import (
    benchmark_encoders,
    collect_hardware_report,
    derive_render_profile,
    report_to_dict,
)
from .profile_cache import ProfileCache

PRERELEASE_NAME = "highlight-desktop-offline-preview"
PRERELEASE_BUILD = "1.0.19-preview.1"
PRODUCTION_APP = Path("D:/Highlight_Video_Studio")
PRODUCTION_PORT = 5080
DEFAULT_FFMPEG = "ffmpeg"


def _resolve_binary(explicit: str | None, name: str) -> str:
    import shutil

    if explicit:
        return explicit
    found = shutil.which(name) or shutil.which(f"{name}.exe")
    if found:
        return found
    local = PRODUCTION_APP / "bin" / f"{name}.exe"
    return str(local) if local.is_file() else name


def _find_ffmpeg(explicit: str | None = None) -> str:
    return _resolve_binary(explicit, "ffmpeg")


def _find_ffprobe(explicit: str | None = None) -> str:
    return _resolve_binary(explicit, "ffprobe")


def production_safety(payload_root: str | Path | None = None) -> dict:
    """Report whether a payload/install operation would disturb production.

    Never starts, stops, or inspects production processes; only reads filesystem facts.
    """
    findings: list[str] = []
    blocked = False
    app_py = PRODUCTION_APP / "web" / "app.py"
    installed_version = None
    if app_py.is_file():
        for line in app_py.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("APP_VERSION") and "=" in stripped:
                installed_version = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                break
    else:
        findings.append("Production app.py not found at the expected path (fine on a clean PC).")

    target = Path(payload_root).resolve() if payload_root else None
    if target is not None:
        if target == PRODUCTION_APP.resolve():
            blocked = True
            findings.append("Refused: target equals the running production directory.")
        elif PRODUCTION_APP.resolve() in target.parents:
            blocked = True
            findings.append("Refused: target is inside the running production directory.")

    return {
        "production_path": str(PRODUCTION_APP),
        "production_version": installed_version,
        "production_port": PRODUCTION_PORT,
        "production_payload_blocked": blocked,
        "findings": findings,
        "touches_production": False,
    }


def environment_report(ffmpeg_bin: str | None = None, ffprobe_bin: str | None = None,
                       temp_dir: str | Path | None = None, cache_path: str | Path | None = None,
                       force: bool = False, run_canary: bool = True) -> dict:
    ffmpeg = _find_ffmpeg(ffmpeg_bin)
    ffprobe = _find_ffprobe(ffprobe_bin)
    probe_dir = Path(temp_dir) if temp_dir else Path(tempfile.mkdtemp(prefix="highlight_probe_"))
    probe_dir.mkdir(parents=True, exist_ok=True)

    report = collect_hardware_report(ffmpeg_bin=ffmpeg, temp_dir=probe_dir)
    canary = benchmark_encoders(report, ffmpeg, ffprobe, probe_dir) if run_canary else {}

    cache = ProfileCache(cache_path or default_cache_path())
    profile = cache.resolve(report, canary_results=canary, force=force)

    return {
        "prerelease_name": PRERELEASE_NAME,
        "build": PRERELEASE_BUILD,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "hardware": report_to_dict(report),
        "canary": canary,
        "render_profile": profile,
        "production_safety": production_safety(),
    }


def default_cache_path() -> Path:
    import os

    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "HighlightVideoStudio" / "cache"
    return base / "render_profile.json"


def default_install_root() -> Path:
    import os

    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs" / PRERELEASE_NAME


def install_plan(payload_root: str | Path | None = None) -> dict:
    """Describe a side-by-side, non-destructive installation. Writes nothing."""
    production = production_safety(payload_root)
    return {
        "prerelease_name": PRERELEASE_NAME,
        "build": PRERELEASE_BUILD,
        "mode": "side-by-side",
        "install_root": str(Path(payload_root).resolve() if payload_root else default_install_root()),
        "data_root": str((Path(payload_root).resolve() if payload_root else default_install_root()) / "data"),
        "runtime_dir": str((Path(payload_root).resolve() if payload_root else default_install_root()) / "run"),
        "bind_host": "127.0.0.1",
        "bind_port": "ephemeral (never 5080)",
        "tunnel_required": False,
        "inbound_port": None,
        "production_safety": production,
        "preserves_existing_data": True,
        "steps": [
            "Resolve a side-by-side directory outside D:\\Highlight_Video_Studio.",
            "Copy payload files; never overwrite production paths.",
            "Reuse existing data by reading config/ledgers, writing only under the payload data root.",
            "Start with the loopback launcher on an ephemeral port; leave port 5080 untouched.",
            "Verify /healthz and hardware profile before enabling render jobs.",
        ],
    }


def write_report(path: str | Path, report: dict | None = None) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = report if report is not None else environment_report()
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


if __name__ == "__main__":  # pragma: no cover - manual run
    print(json.dumps(environment_report(), indent=2, sort_keys=True))
