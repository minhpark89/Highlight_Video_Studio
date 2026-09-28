import json
import time
from pathlib import Path

from .security import canonical_json


class ProfileCache:
    """Cache hardware facts, canary evidence, and the derived render profile."""

    def __init__(self, path: str | Path, ttl_seconds: int = 7 * 24 * 60 * 60):
        self.path = Path(path)
        self.ttl_seconds = ttl_seconds

    def load(self) -> dict | None:
        if not self.path.is_file():
            return None
        try:
            entry = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return entry if isinstance(entry, dict) else None

    def is_valid(self, entry: dict | None, fingerprints: dict, now: int | None = None) -> bool:
        if not entry or entry.get("fingerprints") != fingerprints:
            return False
        return int(entry.get("expires_at", 0)) > (now if now is not None else int(time.time()))

    def save(self, profile: dict, fingerprints: dict, hardware: dict | None = None, canaries: dict | None = None, now: int | None = None) -> dict:
        timestamp = now if now is not None else int(time.time())
        entry = {
            "schema_version": 2,
            "profile": profile,
            "hardware": hardware or {},
            "canaries": canaries or {},
            "fingerprints": fingerprints,
            "saved_at": timestamp,
            "expires_at": timestamp + self.ttl_seconds,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(self.path.name + ".tmp")
        temp.write_text(canonical_json(entry), encoding="utf-8")
        temp.replace(self.path)
        return entry

    def resolve(self, report, canary_results: dict | None = None, force: bool = False) -> dict:
        from .hardware import derive_render_profile, report_to_dict

        cached = self.load()
        if not force and self.is_valid(cached, report.fingerprints):
            return {**cached["profile"], "source": "cache"}
        profile = derive_render_profile(report, canary_results)
        self.save(profile, report.fingerprints, hardware=report_to_dict(report), canaries=canary_results)
        return {**profile, "source": "probe"}


def build_or_load_profile(cache_path: str | Path, ffmpeg_bin: str, ffprobe_bin: str, temp_dir: str | Path, force: bool = False) -> dict:
    """Collect lightweight facts, reuse a valid cache, or run real encoder canaries."""
    from .hardware import collect_hardware_report, derive_render_profile, report_to_dict, run_encoder_canaries

    report = collect_hardware_report(ffmpeg_bin=ffmpeg_bin, temp_dir=Path(temp_dir))
    cache = ProfileCache(cache_path)
    cached = cache.load()
    if not force and cache.is_valid(cached, report.fingerprints):
        return cached
    canaries = run_encoder_canaries(report, ffmpeg_bin, ffprobe_bin, Path(temp_dir))
    profile = derive_render_profile(report, canaries)
    return cache.save(profile, report.fingerprints, hardware=report_to_dict(report), canaries=canaries)
