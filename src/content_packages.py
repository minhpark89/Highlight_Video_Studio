"""Persisted Content Package generation with no-LLM fallbacks and quota protection."""
from __future__ import annotations

import json
import html
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime
from pathlib import Path

import requests
from multi_pc.json_io import replace_with_retry

from multi_pc.data_root import ProcessLease, canonical_data_root
from src.llm_response import chat_model_unavailable, chat_stream_incomplete, json_from_chat_response
from src.text_llm_diagnostics import chat_endpoint, chat_failure
from src.fallback_comments import fallback_first_comment
from src.first_comment_profiles import load_profile_store, profile_first_comment
from src.article_format import normalize_article, viewing_article, word_count
from src.english_text import ENGLISH_INSTRUCTION, assert_english_package, english_or_default, package_is_english, package_summary_is_english

DATA_ROOT = canonical_data_root()
QUEUE_FILE = DATA_ROOT / "data" / "content_packages.json"
CIRCUIT_FILE = DATA_ROOT / "data" / "llm_circuit.json"
_LOCK = threading.RLock()
_WORKER_THREAD = None
_WORKER_LOCK = threading.Lock()
_POST_SYNC_LOCK = threading.RLock()
_SECRET_RE = re.compile(r"(access_token|page_token|token|api_key|secret|password|authorization)\s*[=:]\s*[^\s&\"',]+", re.I)
QUOTA_CODES = {402, 429}
MAX_CONTENT_WORKERS = 32
COMMENT_METADATA = ("first_comment_source", "first_comment_profile_id", "first_comment_profile_name",
                    "first_comment_model", "first_comment_fallback_reason")


def sanitize_error(value, limit=400):
    text = _SECRET_RE.sub(lambda match: match.group(1) + "=[redacted]", str(value or ""))
    return " ".join(text.split())[:limit]


def _read(path: Path, default):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except Exception:
        return default


def _write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        replace_with_retry(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fallback_package(title: str, summary: str = "", article_url: str = "", profile_id: str = "", profile_store=None, niche: str = "") -> dict:
    clean = english_or_default(title, "Original Video")
    context = english_or_default(summary)
    niche = english_or_default(niche)
    hero = clean[:110]
    lead = context or f"A guide to reviewing the original video associated with {clean}."
    article = viewing_article(clean, context, niche)
    link = str(article_url or "").strip()
    comment = profile_first_comment(clean, link, profile_id, profile_store) if link else ""
    caption = f"🔥 {clean}\n\n{lead}\n\nWhat detail did you notice first?\n\n#highlight #viral #trending #mustwatch"
    return {
        "hero_title": hero,
        "article_html": article,
        "first_comment": comment,
        "caption": caption,
        "hashtags": ["#highlight", "#viral", "#trending", "#mustwatch"],
        "source": "no_llm",
        "language": "en",
    }


def fallback_video_label(title: str, video_url: str = "") -> str:
    """Return a YouTube id or Playable hero label for article rendering.

    The website pipeline embeds the original YouTube video when one is known and
    otherwise falls back to a direct MP4 hero block; both paths stay responsive.
    """
    from src.publisher.website_publisher import extract_youtube_video_id

    video_id = extract_youtube_video_id(str(video_url or ""))
    if video_id:
        return video_id
    clean = " ".join(str(title or "Highlight").split()).strip()
    return "" if not clean else clean[:110]


def circuit_status(now=None):
    state = _read(CIRCUIT_FILE, {})
    current = int(now or time.time())
    retry_at = int(state.get("retry_at") or 0)
    return {**state, "open": retry_at > current, "retry_after_seconds": max(0, retry_at - current)}


def record_quota_failure(error, cooldown_seconds=900):
    now = int(time.time())
    previous = _read(CIRCUIT_FILE, {})
    failures = int(previous.get("failures") or 0) + 1
    cooldown = min(21600, max(int(cooldown_seconds), 300 * failures))
    state = {"opened_at": now, "retry_at": now + cooldown, "failures": failures, "reason": sanitize_error(error)}
    _write(CIRCUIT_FILE, state)
    return state


def record_llm_success():
    _write(CIRCUIT_FILE, {"opened_at": 0, "retry_at": 0, "failures": 0, "reason": ""})


def _llm_package(title, summary, video_url="", article_url="", *, niche="", component=""):
    from src.content_builder import get_llm_candidates, _get_task_model

    cfg = get_llm_candidates()
    endpoint = str(cfg.get("configured_base") or "").strip()
    model = _get_task_model("first_comment" if component == "first_comment" else "article") or cfg.get("model")
    if not endpoint:
        raise RuntimeError("Text LLM api_base missing: configure llm.api_base for the text route")
    if not model or not cfg.get("api_key"):
        raise RuntimeError(chat_failure(None, has_key=bool(cfg.get("api_key")), has_model=bool(model)))
    prompt = (
        "Create a content package for a rendered highlight. Return one JSON object ONLY (no reasoning, "
        "markdown or prose) with string keys hero_title, article_html, first_comment, caption, "
        "and an array of strings hashtags. Article HTML must be a useful 750-950 word article, "
        "with exactly one sentence per <p>, clear headings, and frequent paragraph breaks. "
        "Invite readers to scroll to the full video at the end without inventing its outcome. "
        "but do not invent events or facts not supported by the inputs. "
        "If an Article URL is provided, write a unique first_comment tied to this video's title and "
        "include that exact Article URL once. If no Article URL is provided, set first_comment to an empty string.\n"
        f"Title: {title}\nSummary: {summary}\nNiche / editorial direction: {niche}\nSource: {video_url}\nArticle URL: {article_url}"
    )
    if component:
        prompt = (f"Return JSON only with the requested key {component}. Write this component for the video "
                  f"titled {title}. Context: {summary}. Niche: {niche}. "
                  f"For first_comment include this exact URL once: {article_url}; invite the reader to the full video "
                  "at the end of the article, keep under 400 characters, and do not invent details. "
                  "hashtags must be an array of strings; every other component must be a string. "
                  "article_html must be 750-950 words with one sentence per paragraph.")
    prompt = ENGLISH_INSTRUCTION + "\n" + prompt
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = f"Bearer {cfg['api_key']}"
    # A 200 can contain commentary, an empty reasoning-only reply, or incomplete
    # JSON. Retry that *one* response failure with a more explicit instruction;
    # never replay network failures, quota errors or non-200 provider responses.
    messages = [{"role": "user", "content": prompt}]
    for attempt in range(2):
        response = requests.post(
            chat_endpoint(endpoint), headers=headers,
            json={"model": model, "messages": messages, "stream": False,
                  "max_tokens": 4000 if not component or component == "article_html" else 400,
                  "temperature": 0.45 if attempt == 0 else 0.2},
            timeout=(5, 45),
        )
        if response.status_code in QUOTA_CODES:
            raise QuotaError(f"LLM quota HTTP {response.status_code}")
        if response.status_code != 200:
            raise RuntimeError(chat_failure(response.status_code, has_key=True, has_model=True))
        if chat_stream_incomplete(response):
            raise RuntimeError("Text LLM HTTP 200 stream ended without completion; check provider/model route")
        if chat_model_unavailable(response):
            raise RuntimeError("Text LLM model is no longer available on the configured route; select an available text model")
        try:
            data = json_from_chat_response(response)
            if not isinstance(data, dict):
                raise ValueError("LLM returned a non-object content package")
            required = [component] if component and component != "hashtags" else ([] if component else ["hero_title", "article_html", "caption"])
            if not all(isinstance(data.get(key), str) and data[key].strip() for key in required):
                raise ValueError("LLM returned an incomplete content package")
            if component in ("", "first_comment") and not isinstance(data.get("first_comment"), str):
                raise ValueError("LLM returned an incomplete content package")
            if component in ("", "first_comment") and article_url and data["first_comment"].count(article_url) != 1:
                raise ValueError("LLM First Comment must contain the verified article URL exactly once")
            if component in ("", "hashtags") and (not isinstance(data.get("hashtags"), list) or not all(
                isinstance(tag, str) for tag in data["hashtags"]
            )):
                raise ValueError("LLM returned an incomplete content package")
            assert_english_package(data)
        except ValueError:
            if attempt:
                raise
            # Do not echo malformed provider content, which may contain private data.
            messages = [*messages, {"role": "user", "content": (
                "Your previous response could not be used. Return exactly one complete JSON object "
                "with hero_title, article_html, first_comment, caption and hashtags. "
                "No thinking, explanation, fences or extra text. first_comment may be an empty string; "
                "hashtags must be an array of strings. " + ENGLISH_INSTRUCTION
            )}]
            continue
        data["source"] = "llm"
        data["language"] = "en"
        data["llm_model"] = model
        data["first_comment_source"] = "llm" if article_url else "pending_article_url"
        record_llm_success()
        return data


class QuotaError(RuntimeError):
    pass


def generate_package(title, summary="", video_url="", mode="auto", article_url="", component="", profile_id="", profile_store=None, niche="", fallback_strategy=None):
    profile_store = dict(profile_store or load_profile_store(DATA_ROOT / "data" / "first_comment_profiles.json"))
    if fallback_strategy in ("rotate", "deterministic"):
        profile_store["selection_strategy"] = fallback_strategy
    profile_store.setdefault("rotation_path", str(DATA_ROOT / "data" / "first_comment_rotation.json"))
    selected_profile = next((profile for profile in profile_store.get("profiles", [])
                             if profile.get("id") == (profile_id or profile_store.get("default_profile_id"))), {})
    niche = str(niche or selected_profile.get("niche") or "").strip()[:300]
    # Reserve a rotating template only if fallback is actually needed.
    fallback = fallback_package(title, summary, "", profile_id, profile_store, niche)
    selected_mode = str(mode or "auto").lower()
    if selected_mode == "no_llm":
        result = fallback
    elif circuit_status().get("open"):
        if selected_mode == "llm":
            raise RuntimeError("LLM quota circuit open; try again after cooldown")
        result = {**fallback, "source": "no_llm_circuit_open", "circuit": circuit_status()}
    else:
        try:
            result = _llm_package(title, summary, video_url, article_url, niche=niche, component=component)
        except QuotaError as exc:
            if selected_mode == "llm":
                raise RuntimeError(sanitize_error(exc)) from None
            state = record_quota_failure(exc)
            result = {**fallback, "source": "no_llm_quota_fallback", "circuit": {**state, "open": True}}
        except Exception as exc:
            reason = sanitize_error(exc) if isinstance(exc, (RuntimeError, ValueError)) else type(exc).__name__
            if selected_mode == "llm":
                raise RuntimeError(reason) from None
            result = {**fallback, "source": "no_llm_error_fallback", "fallback_reason": reason}
    result["niche"] = niche
    if article_url and str(result.get("source") or "").startswith("no_llm"):
        result["first_comment"] = profile_first_comment(title, article_url, profile_id, profile_store)
    if result.get("article_html"):
        result["article_html"] = normalize_article(result["article_html"])
        result["word_count"] = word_count(result["article_html"])
    if article_url and result.get("first_comment"):
        result.setdefault("first_comment_profile_id", profile_id or profile_store.get("default_profile_id", "builtin_general"))
        result.setdefault("first_comment_source", "template_fallback" if str(result.get("source") or "").startswith("no_llm") else "llm")
        selected_profile = next((p for p in profile_store.get("profiles", []) if p.get("id") == result["first_comment_profile_id"]), {})
        result["first_comment_profile_name"] = selected_profile.get("name", "")
        result["first_comment_model"] = result.get("llm_model", "") if result["first_comment_source"] == "llm" else ""
        result["first_comment_fallback_reason"] = ""
        if result["first_comment_source"] == "template_fallback":
            result["first_comment_fallback_reason"] = sanitize_error(result.get("fallback_reason") or (
                "LLM disabled for this package" if selected_mode == "no_llm" else result.get("source", "")))
    if component:
        if component not in fallback:
            raise ValueError("Unknown content component")
        return {component: result.get(component) or fallback[component], "source": result.get("source"),
                **{key: result.get(key, "") for key in COMMENT_METADATA},
                "llm_model": result.get("llm_model", ""), "fallback_reason": result.get("fallback_reason", "")}
    return result


def enqueue_content_package(*, clip_filename, title, summary="", video_url="", mode="auto", post_ids=None,
                            components=None, article_url="", create_website_article=False, source_job_id="", source_clip_id="",
                            first_comment_profile_id="", niche="", fallback_strategy="rotate",
                            source_sha256="", require_video_upload=False, schedule_priority=None):
    profile_store = load_profile_store(DATA_ROOT / "data" / "first_comment_profiles.json")
    selected_profile_id = str(first_comment_profile_id or profile_store.get("default_profile_id") or "builtin_general")
    selected_profile = next((profile for profile in profile_store["profiles"] if profile["id"] == selected_profile_id), None)
    if not selected_profile:
        raise ValueError("First Comment profile not found.")
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        item = {
            "id": f"content_{int(time.time())}_{uuid.uuid4().hex[:8]}",
            "clip_filename": str(clip_filename or "").strip(),
            "source_job_id": str(source_job_id or "").strip(),
            "source_clip_id": str(source_clip_id or "").strip(),
            "source_sha256": str(source_sha256 or ""),
            "require_video_upload": bool(require_video_upload),
            "title": str(title or ""),
            "summary": str(summary or ""),
            "niche": str(niche or selected_profile.get("niche") or "").strip()[:300],
            "fallback_strategy": fallback_strategy if fallback_strategy in ("rotate", "deterministic") else "rotate",
            "video_url": str(video_url or ""),
            "mode": mode if mode in ("auto", "llm", "no_llm") else "auto",
            "components": components or ["hero_title", "article_html", "first_comment", "caption"],
            "post_ids": list(post_ids or []),
            "schedule_priority": bool(post_ids) if schedule_priority is None else bool(schedule_priority),
            "article_url": str(article_url or ""),
            "first_comment_profile_id": selected_profile_id,
            "first_comment_profile_store": {"default_profile_id": selected_profile_id, "profiles": [selected_profile],
                "selection_strategy": fallback_strategy if fallback_strategy in ("rotate", "deterministic") else "rotate",
                "rotation_path": str(DATA_ROOT / "data" / "first_comment_rotation.json")},
            "embed_status": "ready" if str(video_url or "").strip() else "pending_generation",
            "video_url": str(video_url or ""),
            "create_website_article": bool(create_website_article),
            "status": "queued",
            "attempts": 0,
            "created_at": _now(),
            "result": {},
            "error": "",
        }
        items.append(item)
        _write(QUEUE_FILE, items)
        return item


def ensure_content_package(**kwargs):
    """Atomically reuse pending/finished work by hash before creating a job."""
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        sha = kwargs.get("source_sha256")
        item = next((entry for entry in reversed(items) if
                     (sha and entry.get("source_sha256") == sha) or
                     ((not sha or not entry.get("source_sha256")) and
                      _same_clip(entry, kwargs.get("clip_filename"), kwargs.get("source_job_id", ""),
                                 kwargs.get("source_clip_id", "")))), None)
        if not item:
            return enqueue_content_package(**kwargs)
        item["post_ids"] = list(dict.fromkeys(list(item.get("post_ids") or []) + list(kwargs.get("post_ids") or [])))
        if sha:
            item["source_sha256"] = sha
        requested_clip = str(kwargs.get("clip_filename") or "")
        if item.get("status") in ("queued", "failed", "retryable") and requested_clip:
            old_path = Path(item.get("clip_filename") or "")
            old_path = old_path if old_path.is_absolute() else DATA_ROOT / "output" / old_path
            if not old_path.is_file():
                item["clip_filename"] = requested_clip
        if not item.get("video_url") and kwargs.get("video_url"):
            item["video_url"] = kwargs["video_url"]
        # A text-only cached package cannot satisfy a newly opted-in daily
        # Website plan. Reuse its identity and request the missing CMS work.
        if kwargs.get("create_website_article") and not item.get("create_website_article"):
            item["create_website_article"] = True
            if not item.get("article_url") and item.get("status") == "ready":
                item.update(status="queued", website_status="pending_generation", error="", website_error="")
        # Legacy finished CMS packages already verified the original YouTube
        # embed, before the intake worker had a separate media receipt field.
        # Carry that recorded evidence forward when reusing warehouse content.
        if (not item.get("website_video_status") and item.get("create_website_article")
                and item.get("embed_status") == "ready" and _reusable(item, needs_article=True)):
            from src.publisher.website_publisher import extract_youtube_video_id
            original_id = extract_youtube_video_id(item.get("youtube_id")) or extract_youtube_video_id(item.get("video_url"))
            if original_id:
                item.update({"website_video_status": "youtube_embed_verified", "website_video_source": "youtube",
                             "website_video_url": f"https://www.youtube.com/watch?v={original_id}"})
        if kwargs.get("require_video_upload"):
            item["require_video_upload"] = True
            # A legacy ready YouTube article must be repaired explicitly. It
            # cannot satisfy an upload plan or generate a second CMS article.
            if item.get("status") == "ready" and item.get("website_video_status") != "verified":
                item.update({"status": "failed", "website_status": "failed",
                             "website_error": "Existing article has no verified uploaded video; repair that article before posting.",
                             "error": "Website video verification required."})
        if item.get("status") == "queued":
            item["schedule_priority"] = bool(item.get("schedule_priority") or kwargs.get("schedule_priority", bool(item.get("post_ids"))))
        _write(QUEUE_FILE, items)
        return dict(item)


def list_packages():
    with _LOCK:
        return _read(QUEUE_FILE, [])


def get_package(package_id):
    return next((item for item in list_packages() if item.get("id") == package_id), None)


def reject_cached_package(package_id, error):
    """Quarantine one invalid cached result; retain its CMS URL for explicit retry."""
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        item = next((row for row in items if row.get("id") == package_id), None)
        if not item or item.get("status") != "ready":
            return False
        item.update(status="failed", error=sanitize_error(error), validation_error=sanitize_error(error), updated_at=_now())
        if "article_html" in str(error):
            item.update(website_status="failed", website_error=sanitize_error(error))
        _write(QUEUE_FILE, items)
        return True


def _clip_keys(value):
    """Match clips across absolute/relative paths and legacy basename records."""
    raw = str(value or "").strip()
    if not raw:
        return set()
    path = Path(raw)
    return {raw.casefold(), path.name.casefold()}


def scheduled_video_path(output_dir, clip_filename):
    """Resolve scheduled media only inside this installation's output directory.

    Reject foreign absolute paths and symlinks that escape output; accepting a
    basename for a foreign file could silently publish an unrelated local clip.
    """
    raw = str(clip_filename or "").strip()
    if not raw:
        raise ValueError("Video path is empty")
    root = Path(output_dir).resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("Video must be inside this installation's output directory")
    if not candidate.is_file():
        raise FileNotFoundError(f"Video file not found: {raw}")
    return candidate


def _same_clip(entry, clip_filename, source_job_id="", source_clip_id=""):
    for field, requested in (("source_job_id", source_job_id), ("source_clip_id", source_clip_id)):
        existing = str(entry.get(field) or "").strip()
        if existing and requested and existing != str(requested).strip():
            return False
    if source_job_id and source_clip_id and entry.get("source_job_id") and entry.get("source_clip_id"):
        return (str(entry["source_job_id"]) == str(source_job_id)
                and str(entry["source_clip_id"]) == str(source_clip_id))
    return bool(_clip_keys(entry.get("clip_filename")) & _clip_keys(clip_filename))


def _reusable(entry, *, needs_article, article_url=""):
    if entry.get("status") != "ready" or not (entry.get("result") or {}).get("caption"):
        return False
    if not package_is_english(entry.get("result")):
        return False
    url = str(entry.get("article_url") or "").strip()
    if article_url and url != str(article_url).strip():
        return False
    if needs_article and (not url or entry.get("website_status") != "ready"):
        return False
    return not url or (entry.get("website_status") == "ready" and
                       url in str((entry.get("result") or {}).get("first_comment") or ""))


def package_needs_attention(item):
    """A ready caption does not hide a failed CMS or a missing required comment."""
    source = str((item.get("result") or {}).get("source") or "")
    if not package_summary_is_english(item.get("result")):
        return True
    if item.get("status") in ("failed", "retryable"):
        return True
    if item.get("status") in ("queued", "running"):
        # Imported queues can contain hundreds of fallback packages that are
        # waiting for a real LLM retry. Keep them visible in the repair view.
        return source in ("no_llm_error_fallback", "no_llm_quota_fallback")
    if item.get("website_status") == "failed":
        return True
    if item.get("create_website_article") and not item.get("article_url"):
        return True
    result = item.get("result") or {}
    url = str(item.get("article_url") or "").strip()
    if url and "first_comment" in (item.get("components") or ["first_comment"]):
        if url not in str(result.get("first_comment") or ""):
            return True
    return source in ("no_llm_error_fallback", "no_llm_quota_fallback")


def attach_existing_package(*, clip_filename, post_ids=None, source_job_id="", source_clip_id="", needs_article=True, article_url=""):
    """Attach a finished library package without repeating CMS or LLM work."""
    wanted = [str(value) for value in (post_ids or []) if str(value).strip()]
    keys = _clip_keys(clip_filename)
    if not wanted or not keys:
        return None
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        item = next(
            (entry for entry in reversed(items)
             if _same_clip(entry, clip_filename, source_job_id, source_clip_id)
             and _reusable(entry, needs_article=needs_article, article_url=article_url)),
            None,
        )
        if not item:
            item = next((entry for entry in reversed(items)
                         if _same_clip(entry, clip_filename, source_job_id, source_clip_id)
                         and entry.get("status") in ("queued", "running", "ready", "failed", "retryable")
                         and ((entry.get("result") or {}).get("caption") or
                              (entry.get("status") in ("queued", "running") and
                               (entry.get("article_url") or entry.get("post_ids") or
                                (source_job_id and entry.get("source_job_id")))))
                         and (not article_url or not entry.get("article_url") or entry.get("article_url") == article_url)), None)
        if not item:
            return None
        if item.get("status") not in ("queued", "running") and not _reusable(item, needs_article=needs_article, article_url=article_url):
            if article_url and not item.get("article_url"):
                item["article_url"] = article_url
            item["create_website_article"] = bool(needs_article and not item.get("article_url"))
            # A failed CMS call may have created an article before its response
            # was lost. Preserve that failure for an explicit, informed retry.
            if item.get("website_status") != "failed":
                item["status"] = "queued"
                item["website_status"] = "pending_generation" if item["create_website_article"] else "ready"
                item["website_error"] = ""
                item["error"] = ""
        item["post_ids"] = list(dict.fromkeys(list(item.get("post_ids") or []) + wanted))
        item["updated_at"] = _now()
        _write(QUEUE_FILE, items)
        snapshot = dict(item)
    if snapshot.get("status") == "ready":
        _apply_to_posts(snapshot)
    return snapshot


def component_statuses(item):
    """Return explicit presence/status data for the Content Studio UI."""
    item = item or {}
    result = item.get("result") if isinstance(item.get("result"), dict) else {}
    package_status = str(item.get("status") or "queued")
    output = {}
    for name in ("hero_title", "article_html", "first_comment", "caption", "hashtags"):
        value = result.get(name)
        if value:
            output[name] = {"status": "ready", "present": True}
        elif package_status in ("queued", "running"):
            output[name] = {"status": "pending", "present": False}
        elif package_status in ("retryable", "failed"):
            output[name] = {"status": "retryable", "present": False}
        else:
            output[name] = {"status": "missing", "present": False}
    article_url = str(item.get("article_url") or "").strip()
    website_status = str(item.get("website_status") or ("ready" if article_url else "not_configured"))
    output["website_link"] = {
        "status": website_status,
        "present": bool(article_url),
        "value": article_url,
        "error": sanitize_error(item.get("website_error")) if website_status == "failed" else "",
    }
    if not article_url and item.get("create_website_article"):
        output["first_comment"] = {
            "status": "blocked_website" if website_status == "failed" else "pending",
            "present": False,
        }
    return output


def resolve_article_url(item):
    """Create the CMS article only when the queue item definitely needs one.

    The CMS is called from the background worker, never from schedule creation, so
    a slow or failing CMS can no longer drop an accepted Facebook schedule.
    """
    existing = str(item.get("article_url") or "").strip()
    if existing and not item.get("repair_existing_article"):
        if item.get("require_video_upload") and item.get("website_video_status") != "verified":
            return existing, "failed", "Existing CMS article has no verified uploaded video; repair it before posting."
        if item.get("result") and not package_is_english(item["result"]):
            return existing, "failed", "Existing CMS article contains non-English content. Repair that same URL before reusing or regenerating this package."
        return existing, "ready", ""
    if not existing and not item.get("create_website_article"):
        return "", "not_configured", ""
    try:
        from src.publisher.website_publisher import publish_clip_to_website_cms, repair_existing_website_article

        store = dict(item.get("first_comment_profile_store") or load_profile_store(DATA_ROOT / "data" / "first_comment_profiles.json"))
        store["selection_strategy"] = item.get("fallback_strategy", "rotate")
        store["rotation_path"] = str(DATA_ROOT / "data" / "first_comment_rotation.json")

        def content_factory(expected_url, metadata):
            item["title"] = metadata.get("article_title") or item.get("title", "")
            generated = generate_package(
                item.get("title", ""), item.get("summary") or metadata.get("description", ""),
                item.get("video_url") or metadata.get("youtube_url", ""), item.get("mode", "auto"),
                article_url=expected_url, profile_id=item.get("first_comment_profile_id", ""),
                profile_store=store, niche=item.get("niche", ""),
                fallback_strategy=item.get("fallback_strategy", "rotate"))
            item["result"] = generated
            item["youtube_id"] = metadata.get("youtube_id", "")
            item["video_url"] = metadata.get("youtube_url") or item.get("video_url", "")
            item.pop("regenerate_text", None)
            return generated

        if existing:
            result = repair_existing_website_article(existing, item.get("clip_filename", ""),
                content_factory=content_factory, asset_metadata=item, mode=item.get("mode", "auto"),
                progress=lambda stage: update_package_progress(item, stage))
        else:
            result = publish_clip_to_website_cms(
                item.get("clip_filename", ""), item.get("title", ""), content_factory=content_factory,
                mode=item.get("mode", "auto"), progress=lambda stage: update_package_progress(item, stage),
                asset_metadata=item,
            )
        if isinstance(result, tuple) and len(result) > 1:
            item["website_thumbnail_url"] = str(result[1] or "")
        url = result[0] if isinstance(result, tuple) else str(result or "")
        if not url:
            raise RuntimeError("CMS không trả Website URL")
        return url, "ready", ""
    except Exception as exc:
        return existing, "failed", sanitize_error(exc)


def _apply_to_posts(item):
    if not item.get("post_ids"):
        return
    try:
        from web.posts_store import load_posts_file, save_posts_file
    except ImportError:
        from posts_store import load_posts_file, save_posts_file

    posts_file = DATA_ROOT / "posts.json"
    posts = load_posts_file(posts_file)
    result = item.get("result") or {}
    assert_english_package(result)
    wanted = set(item["post_ids"])
    comments_to_queue = []
    for post in posts:
        if post.get("id") not in wanted:
            continue
        if post.get("content_frozen_at"):
            # An explicit CMS repair may update verification/error fields while
            # preserving every approved social field and dispatched comment.
            if item.get("website_repair_verified_at") and item.get("article_url") == post.get("article_url"):
                for field in ("website_status", "website_error", "website_video_status", "website_video_url",
                              "website_video_source", "website_repair_verified_at"):
                    if field in item:
                        post[field] = item[field]
                post["website_embed_status"] = item.get("embed_status") or "ready"
                post["content_package_status"] = item.get("status", "ready")
                post["content_package_error"] = ""
            continue
        post["content_package_id"] = item["id"]
        post["content_package_status"] = item.get("status", "ready")
        post["content_package_error"] = ""
        post["content_package_source"] = result.get("source")
        if not post.get("first_comment_snapshot") and post.get("first_comment_status") != "posted":
            post["first_comment_source"] = result.get("first_comment_source") or post.get("first_comment_source", "")
            post["first_comment_profile_id"] = item.get("first_comment_profile_id") or result.get("first_comment_profile_id") or post.get("first_comment_profile_id", "")
            post["first_comment_profile_name"] = result.get("first_comment_profile_name") or post.get("first_comment_profile_name", "")
            post["first_comment_model"] = result.get("first_comment_model") or result.get("llm_model", "")
            post["first_comment_fallback_reason"] = sanitize_error(result.get("first_comment_fallback_reason") or result.get("fallback_reason", ""))
        post["content"] = post.get("content", "") if post.get("draft_edited_at") else result.get("caption") or post.get("content", "")
        if result.get("hero_title") and not post.get("draft_edited_at"):
            post["title"] = result["hero_title"]
        if item.get("article_url"):
            post["article_url"] = item["article_url"]
        post["website_embed_status"] = item.get("embed_status") or "unknown"
        post["youtube_id"] = item.get("youtube_id") or ""
        post["video_url"] = item.get("video_url") or ""
        post["website_status"] = item.get("website_status", post.get("website_status"))
        post["website_error"] = item.get("website_error", "")
        post["website_thumbnail_url"] = item.get("hero_image_url") or item.get("website_thumbnail_url", "")
        post["website_image_source"] = item.get("image_source", "")
        post["website_image_count"] = len(item.get("body_image_urls") or []) + bool(post["website_thumbnail_url"])
        post["website_article_word_count"] = result.get("word_count", 0)
        for field in ("website_video_status", "website_video_url", "website_video_source", "website_video_sha256"):
            if item.get(field):
                post[field] = item[field]
        if result.get("first_comment") and post.get("first_comment_status") != "posted" and not post.get("first_comment_snapshot") and not post.get("draft_edited_at"):
            previous_comment_status = post.get("first_comment_status")
            post["first_comment"] = result["first_comment"]
            if not post.get("output_pipeline"):
                post["first_comment_snapshot"] = result["first_comment"]
            # A package may finish after Facebook published without a comment.
            # Do not suggest that an already-published post still has a pending
            # comment dispatch or trigger an implicit second publishing attempt.
            if previous_comment_status not in ("posted", "pending"):
                post["first_comment_status"] = "ready_after_publish" if post.get("status") in ("published", "processing") else "ready"
            post["first_comment_error"] = ""
            if (post.get("status") == "published" and post.get("post_fb_id")
                    and previous_comment_status not in ("posted", "pending")
                    and post.get("token") and post.get("article_url")
                    and str(post["article_url"]) in post["first_comment"]):
                comments_to_queue.append({
                    "post_id": post.get("id"), "object_id": post.get("post_fb_id"),
                    "token": post.get("token"), "token_id": post.get("token_id"),
                    "comment": post["first_comment"],
                })
        if (post.get("status") == "failed" and post.get("retry_stage") == "website_content"
                and not any(post.get(key) for key in ("meta_upload_video_id", "meta_video_id", "meta_post_id", "post_fb_id", "outcome_unknown"))
                and post.get("article_url") and post.get("website_status") == "ready"
                and str(post["article_url"]) in str(post.get("first_comment") or "")):
            post["status"] = "scheduled"
            post["retryable"] = False
            post.pop("schedule_error", None)
            post["error"] = ""
        if post.get("output_pipeline") and post.get("status") in ("preparing", "draft"):
            valid = (post.get("website_status") == "ready" and post.get("article_url")
                     and post["article_url"] in str(post.get("first_comment") or "")
                     and post.get("content") and (post.get("website_video_status") == "verified" or
                          (post.get("website_media_mode") == "youtube" and post.get("website_video_status") == "youtube_embed_verified")))
            if valid:
                post["status"] = "draft"
                today_expired = bool(post.get("schedule_day") and post["schedule_day"] < datetime.now().date().isoformat())
                if today_expired:
                    post["schedule_error"] = "Đã hết ngày đã chọn; chọn Lên lịch hôm nay để hẹn lại."
                if not today_expired and post.get("approval_mode") == "automatic" and post.get("page_id") and post.get("scheduled_time"):
                    post["status"] = "scheduled"
                    post["approved_at"] = _now()
                    post["content_frozen_at"] = _now()
                    post["first_comment_snapshot"] = post["first_comment"]
    save_posts_file(posts_file, posts)
    if comments_to_queue:
        try:
            from src.publisher.first_comment_queue import enqueue_first_comment
            now = int(__import__("time").time())
            for entry in comments_to_queue:
                queued = enqueue_first_comment(
                    entry["object_id"], entry["token"], entry["comment"], now + 5,
                    token_id=entry["token_id"], post_id=entry["post_id"],
                )
                for post in posts:
                    if post.get("id") == entry["post_id"] and queued.get("success"):
                        post["first_comment_status"] = "pending"
            save_posts_file(posts_file, posts)
        except Exception:
            pass


def _apply_failure_to_posts(item):
    if not item.get("post_ids"):
        return
    try:
        from web.posts_store import load_posts_file, save_posts_file
    except ImportError:
        from posts_store import load_posts_file, save_posts_file
    posts_file = DATA_ROOT / "posts.json"
    posts = load_posts_file(posts_file)
    for post in posts:
        if post.get("id") not in item["post_ids"]:
            continue
        if post.get("content_frozen_at") and not post.get("website_retried_at"):
            continue
        post["content_package_status"] = item["status"]
        if item.get("article_url"):
            post["article_url"] = item["article_url"]
        post["website_status"] = item.get("website_status") or post.get("website_status") or "not_configured"
        post["website_error"] = item.get("website_error", "")
        post["content_package_error"] = item.get("error", "")
        if post.get("first_comment_status") == "posted" or post.get("first_comment_snapshot"):
            continue
        post["first_comment_source"] = "failed"
        if not post.get("first_comment"):
            post["first_comment_status"] = "generation_failed"
            post["first_comment_error"] = item.get("error", "")
    save_posts_file(posts_file, posts)



def retry_package_component(package_id, component, mode=None):
    """Regenerate a selected field and persist it to the queue and linked posts."""
    if component not in ("hero_title", "article_html", "first_comment", "caption", "hashtags"):
        raise ValueError("Unknown content component")
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        item = next((entry for entry in items if entry.get("id") == package_id), None)
        if not item:
            return None
        snapshot = dict(item)
    if component == "first_comment" and (snapshot.get("website_status") != "ready" or not snapshot.get("article_url")):
        raise ValueError("First Comment requires a newly published CMS article with original video embed")
    result = generate_package(
        snapshot.get("title", ""), snapshot.get("summary", ""), snapshot.get("video_url", ""),
        mode=mode or snapshot.get("mode", "auto"), component=component,
        article_url=snapshot.get("article_url", ""),
        profile_id=snapshot.get("first_comment_profile_id", ""),
        profile_store=snapshot.get("first_comment_profile_store"),
        niche=snapshot.get("niche", ""),
    )
    if component == "first_comment" and str(result.get(component) or "").count(snapshot["article_url"]) != 1:
        reason = "First Comment must contain the article URL exactly once"
        if (mode or snapshot.get("mode", "auto")) == "llm":
            raise ValueError(reason)
        store = snapshot.get("first_comment_profile_store") or load_profile_store(DATA_ROOT / "data" / "first_comment_profiles.json")
        profile_id = snapshot.get("first_comment_profile_id") or store.get("default_profile_id", "builtin_general")
        profile = next((p for p in store.get("profiles", []) if p.get("id") == profile_id), {})
        result.update({"first_comment": fallback_package(snapshot.get("title", ""), snapshot.get("summary", ""),
            snapshot["article_url"], profile_id, store)["first_comment"], "first_comment_source": "template_fallback",
            "first_comment_profile_id": profile_id, "first_comment_profile_name": profile.get("name", ""),
            "first_comment_model": "", "first_comment_fallback_reason": reason})
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        item = next((entry for entry in items if entry.get("id") == package_id), None)
        if not item:
            return None
        merged = item.get("result") if isinstance(item.get("result"), dict) else {}
        merged[component] = result.get(component)
        if component == "first_comment":
            merged.update({key: result.get(key, "") for key in COMMENT_METADATA})
        else:
            merged["source"] = result.get("source", "unknown")
        # A title/comment-only retry cannot clear an unrelated CMS failure.
        website_failed = item.get("website_status") == "failed"
        item.update({"result": merged, "status": "failed" if website_failed else "ready",
                     "error": item.get("error", "") if website_failed else "", "updated_at": _now()})
        _write(QUEUE_FILE, items)
    if item["status"] == "ready":
        _apply_to_posts(item)
    return {"component": component, "package": merged, "item": item}


def retry_package(package_id, mode=None, *, repair_website=False):
    """Put a failed/retryable package back in the worker queue with optional mode."""
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        item = next((entry for entry in items if entry.get("id") == package_id), None)
        if not item:
            return None
        if item.get("status") in ("queued", "running"):
            return dict(item)
        if not repair_website and not package_needs_attention(item):
            return dict(item)
        if mode is not None:
            if mode not in ("auto", "llm", "no_llm"):
                raise ValueError("Invalid content generation mode")
            item["mode"] = mode
            if mode == "llm" and str((item.get("result") or {}).get("source") or "").startswith("no_llm"):
                item["regenerate_text"] = True
        if str((item.get("result") or {}).get("source") or "") in ("no_llm_error_fallback", "no_llm_quota_fallback"):
            item["regenerate_text"] = True
        if item.get("article_url") and (repair_website or item.get("website_status") == "failed" or not package_is_english(item.get("result") or {})):
            item["repair_existing_article"] = True
        item.update({"status": "queued", "error": "", "updated_at": _now()})
        _write(QUEUE_FILE, items)
        return dict(item)


def process_content_packages_once():
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        running = [entry for entry in items if entry.get("status") == "running"]
        item = next((entry for entry in sorted(items, key=lambda entry: not entry.get("schedule_priority")) if (entry.get("status") == "queued" or
                     (entry.get("status") == "retryable" and not circuit_status().get("open")))
                     and not any(_same_clip(active, entry.get("clip_filename"), entry.get("source_job_id"),
                                           entry.get("source_clip_id")) for active in running)), None)
        if not item:
            return {"processed": 0, "items": items}
        item["status"] = "running"
        item["started_at"] = _now()
        item["stage"] = "preparing"
        item["attempts"] = int(item.get("attempts") or 0) + 1
        _write(QUEUE_FILE, items)
    try:
        # A schedule may enqueue a basename already present in the Content Studio
        # library as an absolute path. Reuse a verified finished package rather
        # than publishing a duplicate CMS article or leaving the post pending.
        prior = None if item.get("repair_existing_article") else next((entry for entry in reversed(items)
                      if entry.get("id") != item.get("id")
                      and _same_clip(entry, item.get("clip_filename"), item.get("source_job_id"), item.get("source_clip_id"))
                      and _reusable(entry, needs_article=bool(item.get("create_website_article") or
                                                       "first_comment" in (item.get("components") or [])),
                                    article_url=item.get("article_url", ""))
                      and (not item.get("require_video_upload") or entry.get("website_video_status") == "verified")), None)
        if prior:
            item.update({"article_url": prior.get("article_url", ""), "website_status": prior.get("website_status", "not_configured"),
                         "website_error": "", "embed_status": prior.get("embed_status") or "ready",
                         "result": dict(prior.get("result") or {}), "status": "ready",
                         "error": "", "completed_at": _now()})
            for field in ("website_video_status", "website_video_url", "website_video_source", "website_video_sha256"):
                if prior.get(field):
                    item[field] = prior[field]
        else:
            _process_new_content_package(item)
    except Exception as exc:
        item.update({"status": "retryable" if isinstance(exc, QuotaError) else "failed", "error": sanitize_error(exc), "completed_at": _now()})
    with _LOCK:
        latest = _read(QUEUE_FILE, [])
        for index, existing in enumerate(latest):
            if existing.get("id") == item.get("id"):
                item["post_ids"] = list(dict.fromkeys(list(item.get("post_ids") or []) + list(existing.get("post_ids") or [])))
                latest[index] = item
                break
        _write(QUEUE_FILE, latest)
    try:
        with _POST_SYNC_LOCK:
            if item.get("status") == "ready":
                _apply_to_posts(item)
            elif item.get("status") in ("failed", "retryable"):
                _apply_failure_to_posts(item)
    except Exception as post_exc:
        item["error"] = sanitize_error(f"{item.get('error', '')}; post sync: {post_exc}")
        with _LOCK:
            current = _read(QUEUE_FILE, [])
            for entry in current:
                if entry.get("id") == item.get("id"):
                    entry["error"] = item["error"]
            _write(QUEUE_FILE, current)
    return {"processed": 1, "item": item, "items": latest}


def _process_new_content_package(item):
        article_url, website_status, website_error = resolve_article_url(item)
        item["article_url"] = article_url
        item["website_status"] = website_status
        item["website_error"] = website_error
        item["embed_status"] = "ready" if website_status == "ready" and article_url else "failed"
        # Generate the comment after the CMS URL is known so the persisted
        # first comment contains the exact website link shown in Post Management.
        requires_comment = ("first_comment" in (item.get("components") or ["first_comment"])
                            and bool(item.get("create_website_article") or article_url))
        if requires_comment and (website_status != "ready" or not article_url):
            raise RuntimeError(website_error or "First Comment requires a newly published CMS article with original video embed")
        # Keep already generated article/caption when only the CMS link or
        # comment needs repair. This also avoids spending another LLM call.
        result = dict(item.get("result") or {})
        if item.get("regenerate_text") or not result.get("caption") or not result.get("article_html") or not package_is_english(result):
            store = dict(item.get("first_comment_profile_store") or load_profile_store(DATA_ROOT / "data" / "first_comment_profiles.json"))
            store["selection_strategy"] = item.get("fallback_strategy") or store.get("selection_strategy", "rotate")
            store["rotation_path"] = str(DATA_ROOT / "data" / "first_comment_rotation.json")
            result = generate_package(
                item["title"], item.get("summary", ""), item.get("video_url", ""),
                item.get("mode", "auto"), article_url=article_url,
                profile_id=item.get("first_comment_profile_id", ""),
                profile_store=store, niche=item.get("niche", ""),
                fallback_strategy=item.get("fallback_strategy", "rotate"),
            )
        if requires_comment:
            comment = str(result.get("first_comment") or "").strip()
            if not comment or comment.count(article_url) != 1:
                comment_result = generate_package(
                    item["title"], item.get("summary", ""), item.get("video_url", ""),
                    mode=item.get("mode", "auto"), article_url=article_url, component="first_comment",
                    profile_id=item.get("first_comment_profile_id", ""),
                    profile_store=item.get("first_comment_profile_store"), niche=item.get("niche", ""),
                    fallback_strategy=item.get("fallback_strategy", "rotate"),
                )
                result["first_comment"] = comment_result.get("first_comment", "")
                result.update({key: comment_result.get(key, "") for key in COMMENT_METADATA})
            elif not result.get("first_comment_source"):
                result["first_comment_source"] = "template_fallback" if str(result.get("source") or "").startswith("no_llm") else "llm"
            if not result.get("first_comment") or result["first_comment"].count(article_url) != 1:
                raise RuntimeError("First Comment không chứa đúng URL bài CMS mới")
        item.update({"status": "ready", "stage": "complete", "result": result, "error": "", "completed_at": _now()})
        item.pop("regenerate_text", None)


def update_package_progress(item, stage):
    item["stage"] = stage
    item["stage_started_at"] = _now()
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        for entry in items:
            if entry.get("id") == item.get("id"):
                entry.update({"stage": stage, "stage_started_at": item["stage_started_at"]})
                if item.get("result"):
                    entry["result"] = item["result"]
                break
        _write(QUEUE_FILE, items)


def content_worker_settings(workers=None):
    path = DATA_ROOT / "data" / "content_worker_settings.json"
    with _LOCK:
        settings = _read(path, {"workers": 2})
        if workers is not None:
            if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= MAX_CONTENT_WORKERS:
                raise ValueError(f"Số luồng Content/LLM phải là số nguyên từ 1 đến {MAX_CONTENT_WORKERS}.")
            settings = {"workers": workers}
            _write(path, settings)
        saved = settings.get("workers", 2)
        if isinstance(saved, bool) or not isinstance(saved, int) or not 1 <= saved <= MAX_CONTENT_WORKERS:
            raise ValueError(f"Số luồng Content/LLM đã lưu phải là số nguyên từ 1 đến {MAX_CONTENT_WORKERS}.")
        return {"workers": saved, "max_workers": MAX_CONTENT_WORKERS}


def content_worker_status():
    from multi_pc.data_root import _local_pid_alive
    alive = bool(_WORKER_THREAD and _WORKER_THREAD.is_alive())
    if not alive:
        try:
            owner = (DATA_ROOT / "run" / "content-package-worker.lease" / "owner").read_text()
            fields = dict(line.split("=", 1) for line in owner.splitlines() if "=" in line)
            alive = fields.get("host") == __import__("socket").gethostname() and _local_pid_alive(int(fields.get("pid") or 0))
        except (OSError, ValueError):
            pass
    return {"alive": alive, **content_worker_settings()}


def recover_abandoned_packages():
    """Call only after acquiring the exclusive worker lease."""
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        changed = False
        for item in items:
            if item.get("status") != "running":
                continue
            if item.get("create_website_article") and not item.get("article_url"):
                item.update({"status": "failed", "website_status": "failed",
                             "website_error": "Lần tạo Website trước bị gián đoạn; kiểm tra CMS trước khi thử lại để tránh đăng trùng.",
                             "error": "Cần đối soát Website sau khi worker dừng giữa chừng."})
            else:
                item.update({"status": "queued", "error": "Worker trước đã dừng; tiếp tục tạo nội dung."})
            item["recovered_at"] = _now()
            changed = True
        if changed:
            _write(QUEUE_FILE, items)
    return changed


def _worker_loop():
    lease = ProcessLease("content-package-worker", DATA_ROOT, stale_after=120)
    if not lease.acquire():
        return
    try:
        recover_abandoned_packages()
        with ThreadPoolExecutor(max_workers=MAX_CONTENT_WORKERS, thread_name_prefix="content-video") as pool:
            active = set()
            while True:
                lease.touch()
                finished = {future for future in active if future.done()}
                for future in finished:
                    try:
                        future.result()
                    except Exception:
                        pass
                active -= finished
                limit = content_worker_settings()["workers"]
                if any(item.get("status") == "queued" or (item.get("status") == "retryable" and
                       not circuit_status().get("open")) for item in list_packages()):
                    for _ in range(max(0, limit - len(active))):
                        active.add(pool.submit(process_content_packages_once))
                if active:
                    wait(active, timeout=0.5, return_when=FIRST_COMPLETED)
                time.sleep(0.25 if active else 1)
    finally:
        lease.release()


def start_content_package_worker():
    global _WORKER_THREAD
    with _WORKER_LOCK:
        if _WORKER_THREAD and _WORKER_THREAD.is_alive():
            return _WORKER_THREAD
        _WORKER_THREAD = threading.Thread(target=_worker_loop, daemon=True, name="content-package-worker")
        _WORKER_THREAD.start()
        return _WORKER_THREAD
