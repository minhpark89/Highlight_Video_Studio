"""Persisted Content Package generation with no-LLM fallbacks and quota protection."""
from __future__ import annotations

import json
import html
import os
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests
from multi_pc.json_io import replace_with_retry

from multi_pc.data_root import ProcessLease, canonical_data_root
from src.llm_response import chat_model_unavailable, chat_stream_incomplete, json_from_chat_response
from src.text_llm_diagnostics import chat_endpoint, chat_failure
from src.fallback_comments import fallback_first_comment
from src.first_comment_profiles import load_profile_store, profile_first_comment

DATA_ROOT = canonical_data_root()
QUEUE_FILE = DATA_ROOT / "data" / "content_packages.json"
CIRCUIT_FILE = DATA_ROOT / "data" / "llm_circuit.json"
_LOCK = threading.RLock()
_WORKER_THREAD = None
_WORKER_LOCK = threading.Lock()
_SECRET_RE = re.compile(r"(access_token|page_token|token|api_key|secret|password|authorization)\s*[=:]\s*[^\s&\"',]+", re.I)
QUOTA_CODES = {402, 429}
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


def fallback_package(title: str, summary: str = "", article_url: str = "", profile_id: str = "", profile_store=None) -> dict:
    clean = " ".join(str(title or "Untold Highlight").split()).strip()
    context = " ".join(str(summary or "").split()).strip()
    hero = clean[:110]
    lead = context or f"A guide to reviewing the original video associated with {clean}."
    article = (
        f"<h2>{html.escape(hero)}</h2><p>{html.escape(lead)}</p>"
        "<h3>Start with the source</h3><p>Watch the original full-length recording before drawing conclusions from a short highlight or its title. Identify the relevant passage and note what appears before and after it. A title and a short description provide a subject, not independent confirmation of what happened, who was involved, or how the event ended. If the source is unavailable, this guide cannot verify those details.</p>"
        "<h3>Review the sequence</h3><p>Replay the relevant passage at normal speed, then pause at the start, middle and end. Compare what is actually visible across those points. Notice when a cut, camera change, replay or overlay changes the view. A still image can help locate a moment in the source but cannot establish continuity on its own. Keep direct observations separate from interpretation, and leave details unresolved if the video does not show them clearly.</p>"
        "<h3>Check the context</h3><p>Look at the surrounding minutes to see whether they add context to the selected passage. On-screen captions, audio and a camera angle can be useful clues, but none should be presented as a verified outside source without corroboration. The recording may show actions in frame while leaving motivations, audience reactions and events outside the frame unknown. Return to the original footage for any claim that matters, and seek an independent source if the claim goes beyond what the recording can support.</p>"
        "<h3>What remains open</h3><p>This no-LLM overview deliberately does not invent a result, a quote, a location or a cause. The full video is the reference for judging the selected moment; the article is a viewing guide rather than a reported account. If a decisive detail is not visible, describe the uncertainty instead of treating an attractive narrative as evidence.</p>"
    )
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


def _llm_package(title, summary, video_url="", article_url=""):
    from src.content_builder import get_llm_candidates, _get_task_model

    cfg = get_llm_candidates()
    endpoint = str(cfg.get("configured_base") or "").strip()
    model = _get_task_model("content_package") or cfg.get("model")
    if not endpoint:
        raise RuntimeError("Text LLM api_base missing: configure llm.api_base for the text route")
    if not model or not cfg.get("api_key"):
        raise RuntimeError(chat_failure(None, has_key=bool(cfg.get("api_key")), has_model=bool(model)))
    prompt = (
        "Create a content package for a rendered highlight. Return one JSON object ONLY (no reasoning, "
        "markdown or prose) with string keys hero_title, article_html, first_comment, caption, "
        "and an array of strings hashtags. Article HTML must be a useful 350+ word story, "
        "but do not invent events or facts not supported by the inputs. "
        "If an Article URL is provided, write a unique first_comment tied to this video's title and "
        "include that exact Article URL once. If no Article URL is provided, set first_comment to an empty string.\n"
        f"Title: {title}\nSummary: {summary}\nSource: {video_url}\nArticle URL: {article_url}"
    )
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
                  "max_tokens": 2048, "temperature": 0.45 if attempt == 0 else 0.2},
            timeout=45,
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
            if not all(isinstance(data.get(key), str) and data[key].strip()
                       for key in ("hero_title", "article_html", "caption")):
                raise ValueError("LLM returned an incomplete content package")
            if not isinstance(data.get("first_comment"), str):
                raise ValueError("LLM returned an incomplete content package")
            if article_url and data["first_comment"].count(article_url) != 1:
                raise ValueError("LLM First Comment must contain the verified article URL exactly once")
            if not isinstance(data.get("hashtags"), list) or not all(
                isinstance(tag, str) for tag in data["hashtags"]
            ):
                raise ValueError("LLM returned an incomplete content package")
        except ValueError:
            if attempt:
                raise
            # Do not echo malformed provider content, which may contain private data.
            messages = [*messages, {"role": "user", "content": (
                "Your previous response could not be used. Return exactly one complete JSON object "
                "with hero_title, article_html, first_comment, caption and hashtags. "
                "No thinking, explanation, fences or extra text. first_comment may be an empty string; "
                "hashtags must be an array of strings."
            )}]
            continue
        data["source"] = "llm"
        data["llm_model"] = model
        data["first_comment_source"] = "llm" if article_url else "pending_article_url"
        record_llm_success()
        return data


class QuotaError(RuntimeError):
    pass


def generate_package(title, summary="", video_url="", mode="auto", article_url="", component="", profile_id="", profile_store=None):
    profile_store = profile_store or load_profile_store(DATA_ROOT / "data" / "first_comment_profiles.json")
    fallback = fallback_package(title, summary, article_url, profile_id, profile_store)
    selected_mode = str(mode or "auto").lower()
    if selected_mode == "no_llm":
        result = fallback
    elif circuit_status().get("open"):
        if selected_mode == "llm":
            raise RuntimeError("LLM quota circuit open; try again after cooldown")
        result = {**fallback, "source": "no_llm_circuit_open", "circuit": circuit_status()}
    else:
        try:
            result = _llm_package(title, summary, video_url, article_url)
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
                            first_comment_profile_id=""):
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
            "title": str(title or ""),
            "summary": str(summary or ""),
            "video_url": str(video_url or ""),
            "mode": mode if mode in ("auto", "llm", "no_llm") else "auto",
            "components": components or ["hero_title", "article_html", "first_comment", "caption"],
            "post_ids": list(post_ids or []),
            "article_url": str(article_url or ""),
            "first_comment_profile_id": selected_profile_id,
            "first_comment_profile_store": {"default_profile_id": selected_profile_id, "profiles": [selected_profile]},
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


def list_packages():
    with _LOCK:
        return _read(QUEUE_FILE, [])


def get_package(package_id):
    return next((item for item in list_packages() if item.get("id") == package_id), None)


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
    if existing:
        return existing, "ready", ""
    if not item.get("create_website_article"):
        return "", "not_configured", ""
    try:
        from src.publisher.website_publisher import publish_clip_to_website_cms

        result = publish_clip_to_website_cms(
            item.get("clip_filename", ""),
            item.get("title", ""),
        )
        url = result[0] if isinstance(result, tuple) else str(result or "")
        if not url:
            raise RuntimeError("CMS không trả Website URL")
        return url, "ready", ""
    except Exception as exc:
        return "", "failed", sanitize_error(exc)


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
    wanted = set(item["post_ids"])
    comments_to_queue = []
    for post in posts:
        if post.get("id") not in wanted:
            continue
        post["content_package_id"] = item["id"]
        post["content_package_status"] = item.get("status", "ready")
        post["content_package_source"] = result.get("source")
        if not post.get("first_comment_snapshot") and post.get("first_comment_status") != "posted":
            post["first_comment_source"] = result.get("first_comment_source") or post.get("first_comment_source", "")
            post["first_comment_profile_id"] = item.get("first_comment_profile_id") or result.get("first_comment_profile_id") or post.get("first_comment_profile_id", "")
            post["first_comment_profile_name"] = result.get("first_comment_profile_name") or post.get("first_comment_profile_name", "")
            post["first_comment_model"] = result.get("first_comment_model") or result.get("llm_model", "")
            post["first_comment_fallback_reason"] = sanitize_error(result.get("first_comment_fallback_reason") or result.get("fallback_reason", ""))
        post["content"] = result.get("caption") or post.get("content", "")
        if result.get("hero_title"):
            post["title"] = result["hero_title"]
        if item.get("article_url"):
            post["article_url"] = item["article_url"]
        post["website_embed_status"] = item.get("embed_status") or "unknown"
        post["youtube_id"] = item.get("youtube_id") or ""
        post["video_url"] = item.get("video_url") or ""
        post["website_status"] = item.get("website_status", post.get("website_status"))
        post["website_error"] = item.get("website_error", "")
        if result.get("first_comment") and post.get("first_comment_status") != "posted" and not post.get("first_comment_snapshot"):
            previous_comment_status = post.get("first_comment_status")
            post["first_comment"] = result["first_comment"]
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
                and post.get("article_url") and post.get("website_status") == "ready"
                and str(post["article_url"]) in str(post.get("first_comment") or "")):
            post["status"] = "scheduled"
            post["retryable"] = False
            post.pop("schedule_error", None)
            post["error"] = ""
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


def retry_package(package_id, mode=None):
    """Put a failed/retryable package back in the worker queue with optional mode."""
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        item = next((entry for entry in items if entry.get("id") == package_id), None)
        if not item:
            return None
        if item.get("status") in ("queued", "running"):
            return dict(item)
        if not package_needs_attention(item):
            return dict(item)
        if mode is not None:
            if mode not in ("auto", "llm", "no_llm"):
                raise ValueError("Invalid content generation mode")
            item["mode"] = mode
            if mode == "llm" and str((item.get("result") or {}).get("source") or "").startswith("no_llm"):
                item["regenerate_text"] = True
        if str((item.get("result") or {}).get("source") or "") in ("no_llm_error_fallback", "no_llm_quota_fallback"):
            item["regenerate_text"] = True
        item.update({"status": "queued", "error": "", "updated_at": _now()})
        _write(QUEUE_FILE, items)
        return dict(item)


def process_content_packages_once():
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        item = next((entry for entry in items if entry.get("status") == "queued" or (entry.get("status") == "retryable" and not circuit_status().get("open"))), None)
        if not item:
            return {"processed": 0, "items": items}
        item["status"] = "running"
        item["started_at"] = _now()
        item["attempts"] = int(item.get("attempts") or 0) + 1
        _write(QUEUE_FILE, items)
    try:
        # A schedule may enqueue a basename already present in the Content Studio
        # library as an absolute path. Reuse a verified finished package rather
        # than publishing a duplicate CMS article or leaving the post pending.
        prior = next((entry for entry in reversed(items)
                      if entry.get("id") != item.get("id")
                      and _same_clip(entry, item.get("clip_filename"), item.get("source_job_id"), item.get("source_clip_id"))
                      and _reusable(entry, needs_article=bool(item.get("create_website_article") or
                                                       "first_comment" in (item.get("components") or [])),
                                    article_url=item.get("article_url", ""))), None)
        if prior:
            item.update({"article_url": prior.get("article_url", ""), "website_status": prior.get("website_status", "not_configured"),
                         "website_error": "", "embed_status": prior.get("embed_status") or "ready",
                         "result": dict(prior.get("result") or {}), "status": "ready",
                         "error": "", "completed_at": _now()})
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
        if item.get("status") == "ready":
            _apply_to_posts(item)
        elif item.get("status") in ("failed", "retryable"):
            _apply_failure_to_posts(item)
    except Exception as post_exc:
        item["error"] = sanitize_error(f"{item.get('error', '')}; post sync: {post_exc}")
        with _LOCK:
            _write(QUEUE_FILE, latest)
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
        if (item.get("regenerate_text") or
                str(result.get("source") or "") in ("no_llm_error_fallback", "no_llm_quota_fallback") or
                not result.get("caption") or not result.get("article_html")):
            result = generate_package(
                item["title"], item.get("summary", ""), item.get("video_url", ""),
                item.get("mode", "auto"), article_url=article_url,
                profile_id=item.get("first_comment_profile_id", ""),
                profile_store=item.get("first_comment_profile_store"),
            )
        if requires_comment:
            comment = str(result.get("first_comment") or "").strip()
            if not comment or comment.count(article_url) != 1:
                comment_result = generate_package(
                    item["title"], item.get("summary", ""), item.get("video_url", ""),
                    mode=item.get("mode", "auto"), article_url=article_url, component="first_comment",
                    profile_id=item.get("first_comment_profile_id", ""),
                    profile_store=item.get("first_comment_profile_store"),
                )
                result["first_comment"] = comment_result.get("first_comment", "")
                result.update({key: comment_result.get(key, "") for key in COMMENT_METADATA})
            elif not result.get("first_comment_source"):
                result["first_comment_source"] = "template_fallback" if str(result.get("source") or "").startswith("no_llm") else "llm"
            if not result.get("first_comment") or result["first_comment"].count(article_url) != 1:
                raise RuntimeError("First Comment không chứa đúng URL bài CMS mới")
        retryable = str(result.get("source") or "").startswith("no_llm_quota_fallback")
        item.update({"status": "retryable" if retryable else "ready", "result": result, "error": "" if not retryable else "LLM quota exhausted; sẽ tự retry khi quota khả dụng.", "completed_at": _now()})
        if not retryable:
            item.pop("regenerate_text", None)


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
        while True:
            lease.touch()
            result = process_content_packages_once()
            time.sleep(1 if result.get("processed") else 3)
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
