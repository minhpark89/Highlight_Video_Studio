import json
import time
from pathlib import Path

from .security import canonical_json


class ProfileCache:
    """Cache a derived render profile and re-probe when hardware/driver changes."""

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
        if not entry:
            return False
        if entry.get("fingerprints") != fingerprints:
            return False
        return int(entry.get("expires_at", 0)) > (now if now is not None else int(time.time()))

    def save(self, profile: dict, fingerprints: dict, now: int | None = None) -> dict:
        timestamp = now if now is not None else int(time.time())
        entry = {"profile": profile, "fingerprints": fingerprints, "saved_at": timestamp, "expires_at": timestamp + self.ttl_seconds}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(canonical_json(entry), encoding="utf-8")
        temp.replace(self.path)
        return entry

    def resolve(self, report, canary_results: dict | None = None, force: bool = False) -> dict:
        from .hardware import derive_render_profile

        cached = self.load()
        if not force and self.is_valid(cached, report.fingerprints):
            return {**cached["profile"], "source": "cache"}
        profile = derive_render_profile(report, canary_results)
        self.save(profile, report.fingerprints)
        return {**profile, "source": "probe"}
