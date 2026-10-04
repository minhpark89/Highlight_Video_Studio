"""Local First Comment niche profiles and deterministic link-safe fallbacks."""
from __future__ import annotations

import json
import uuid
import threading
from pathlib import Path

from src.fallback_comments import LEAD_INS, fallback_first_comment
from multi_pc.data_root import canonical_data_root
from multi_pc.json_io import replace_with_retry
from src.english_text import assert_english, is_english

_ROTATION_LOCK = threading.RLock()


PROFILE_LABELS = {
    "police": "public safety clip",
    "sports": "sports footage",
    "news": "news video",
    "rescue": "rescue footage",
    "reality": "reality TV scene",
    "general": "original video",
}


def builtin_profiles():
    result = []
    for niche, label in PROFILE_LABELS.items():
        lead_ins = list(LEAD_INS) if niche == "general" else [
            f"For more context on this {label}, {lead[0].lower() + lead[1:]}" for lead in LEAD_INS
        ]
        result.append({
            "id": f"builtin_{niche}", "name": niche.title(), "niche": niche,
            "lead_ins": lead_ins, "builtin": True,
        })
    return result


def _valid_lead_ins(values, *, minimum=30):
    if not isinstance(values, list):
        raise ValueError("Templates must be a list of lead-in sentences.")
    clean = [" ".join(str(value or "").split()).strip() for value in values]
    if len(clean) < minimum:
        raise ValueError(f"A profile needs at least {minimum} First Comment templates.")
    seen = set()
    for value in clean:
        if not value or len(value) > 220 or "http://" in value.lower() or "https://" in value.lower():
            raise ValueError("Templates must be 1–220 characters and must not contain a URL.")
        assert_english(value, "First Comment template")
        key = value.casefold()
        if key in seen:
            raise ValueError("Templates must be unique within a profile.")
        seen.add(key)
    return clean


def normalize_profile(payload, *, profile_id=None, builtin=False):
    niche = str(payload.get("niche") or "general").strip().lower()
    if not niche or len(niche) > 120:
        raise ValueError("Niche must be between 1 and 120 characters.")
    name = " ".join(str(payload.get("name") or niche.title()).split()).strip()
    if not name or len(name) > 80:
        raise ValueError("Profile name must be between 1 and 80 characters.")
    return {
        "id": str(profile_id or payload.get("id") or f"fcprof_{uuid.uuid4().hex}"),
        "name": name, "niche": niche,
        "lead_ins": _valid_lead_ins(payload.get("lead_ins")),
        "fallback_strategy": payload.get("fallback_strategy") if payload.get("fallback_strategy") in ("rotate", "deterministic") else "rotate",
        "builtin": bool(builtin),
    }


def load_profile_store(path: Path):
    path = Path(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError
        profiles = value.get("profiles")
        if not isinstance(profiles, list):
            raise ValueError
        clean = [normalize_profile(profile, profile_id=profile.get("id"), builtin=profile.get("builtin", False)) for profile in profiles]
        if not clean or len({profile["id"] for profile in clean}) != len(clean):
            raise ValueError
        default_id = str(value.get("default_profile_id") or "")
        if default_id not in {profile["id"] for profile in clean}:
            default_id = clean[0]["id"]
        return {"profiles": clean, "default_profile_id": default_id}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {"profiles": builtin_profiles(), "default_profile_id": "builtin_general"}


def save_profile_store(path: Path, value):
    path = Path(path)
    profiles = [normalize_profile(profile, profile_id=profile.get("id"), builtin=profile.get("builtin", False)) for profile in value.get("profiles", [])]
    ids = [profile["id"] for profile in profiles]
    if len(ids) != len(set(ids)):
        raise ValueError("Profile IDs must be unique.")
    default_id = str(value.get("default_profile_id") or "")
    if default_id not in set(ids):
        raise ValueError("Choose an existing default profile.")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps({"default_profile_id": default_id, "profiles": profiles}, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    return {"profiles": profiles, "default_profile_id": default_id}


def profile_first_comment(title: str, article_url: str, profile_id: str = "", store=None) -> str:
    from hashlib import sha256
    from urllib.parse import urlsplit

    url = str(article_url or "").strip()
    try:
        parsed = urlsplit(url)
    except ValueError:
        return ""
    if any(character.isspace() for character in url):
        return ""
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
        return ""
    store = store or {"profiles": builtin_profiles(), "default_profile_id": "builtin_general"}
    target = str(profile_id or store.get("default_profile_id") or "builtin_general")
    profile = next((item for item in store.get("profiles", []) if str(item.get("id")) == target), None)
    if not profile:
        profile = next((item for item in store.get("profiles", []) if str(item.get("id")) == "builtin_general"), None)
    lead_ins = [line for line in ((profile or {}).get("lead_ins") or list(LEAD_INS)) if is_english(line)] or list(LEAD_INS)
    strategy = store.get("selection_strategy") or (profile or {}).get("fallback_strategy", "deterministic")
    if str((profile or {}).get("id")) == "builtin_general" and strategy != "rotate":
        return fallback_first_comment(title, url)
    key = f"{title}\n{url}\n{target}".encode("utf-8")
    if strategy == "rotate":
        # Persist only digests and indices. The same article keeps its selection
        # across retries; new articles consume every sample before wrapping.
        path = Path(store.get("rotation_path") or canonical_data_root() / "data" / "first_comment_rotation.json")
        digest = sha256(key).hexdigest()
        pool = sha256((target + "\n" + "\n".join(lead_ins)).encode("utf-8")).hexdigest()
        with _ROTATION_LOCK:
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                state = {}
            history = state.setdefault(pool, {"next": 0, "articles": {}})
            if digest not in history["articles"]:
                history["articles"][digest] = int(history["next"]) % len(lead_ins)
                history["next"] = int(history["next"]) + 1
                if len(history["articles"]) > 3000:
                    del history["articles"][next(iter(history["articles"]))]
                path.parent.mkdir(parents=True, exist_ok=True)
                temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
                try:
                    temp.write_text(json.dumps(state), encoding="utf-8")
                    replace_with_retry(temp, path)
                finally:
                    temp.unlink(missing_ok=True)
            index = history["articles"][digest]
    else:
        index = int.from_bytes(sha256(key).digest()[:8], "big") % len(lead_ins)
    return f"{lead_ins[index]} {url}"
