"""Persisted Content Package generation with no-LLM fallbacks and quota protection."""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests

from multi_pc.data_root import ProcessLease, canonical_data_root
from src.llm_response import json_from_chat_response

DATA_ROOT = canonical_data_root()
QUEUE_FILE = DATA_ROOT / "data" / "content_packages.json"
CIRCUIT_FILE = DATA_ROOT / "data" / "llm_circuit.json"
_LOCK = threading.RLock()
_WORKER_THREAD = None
_WORKER_LOCK = threading.Lock()
_SECRET_RE = re.compile(r"(access_token|page_token|token|api_key|secret|password|authorization)[=:\s]+[^\s&\"',]+", re.I)
QUOTA_CODES = {402, 429}


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
    os.replace(temp, path)


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fallback_package(title: str, summary: str = "", article_url: str = "") -> dict:
    clean = " ".join(str(title or "Untold Highlight").split()).strip()
    context = " ".join(str(summary or "").split()).strip()
    hero = f"THE MOMENT EVERYONE MISSED: {clean}"[:110]
    lead = context or "A split-second decision changed the direction of the entire scene, and the detail is easy to miss on a first viewing."
    article = (
        f"<h2>{hero}</h2><p>{lead}</p>"
        "<p>The opening sequence establishes the pressure immediately. Small changes in timing, spacing, and reaction create the decisive turning point, while the people involved have almost no time to adjust.</p>"
        "<h3>What changed the outcome</h3><p>Viewed carefully, the key moment is not a single dramatic gesture but a chain of choices. Each response narrows the available options until the final result becomes unavoidable.</p>"
        "<h3>Why viewers are replaying it</h3><p>The full sequence rewards a second look because the most important clue appears before the obvious climax. Watch the complete footage and compare the setup with the aftermath.</p>"
    )
    link = str(article_url or "").strip()
    comment = "👀 Watch the setup again—the detail just before the turning point explains everything."
    if link:
        comment += f" Full breakdown: {link}"
    else:
        comment = ""  # No First Comment without a newly published article.
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


def _llm_package(title, summary, video_url=""):
    from src.content_builder import get_llm_candidates, _get_task_model

    cfg = get_llm_candidates()
    endpoint = str(cfg.get("configured_base") or ((cfg.get("endpoints") or [""])[0]) or "").rstrip("/")
    model = _get_task_model("content_package") or cfg.get("model")
    if not endpoint or not model:
        raise RuntimeError("LLM content package is not configured")
    prompt = (
        "Create a content package for a rendered highlight. Return JSON only with keys "
        "hero_title, article_html, first_comment, caption, hashtags. Article HTML must be a useful 350+ word story.\n"
        f"Title: {title}\nSummary: {summary}\nSource: {video_url}"
    )
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = f"Bearer {cfg['api_key']}"
    response = requests.post(
        f"{endpoint}/chat/completions",
        headers=headers,
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.45},
        timeout=45,
    )
    if response.status_code in QUOTA_CODES:
        raise QuotaError(f"LLM quota HTTP {response.status_code}")
    response.raise_for_status()
    data = json_from_chat_response(response)
    if not isinstance(data, dict):
        raise RuntimeError("LLM returned a non-object content package")
    required = ("hero_title", "article_html", "first_comment", "caption")
    if not all(str(data.get(key) or "").strip() for key in required):
        raise RuntimeError("LLM returned an incomplete content package")
    data["source"] = "llm"
    record_llm_success()
    return data


class QuotaError(RuntimeError):
    pass


def generate_package(title, summary="", video_url="", mode="auto", article_url="", component=""):
    fallback = fallback_package(title, summary, article_url)
    selected_mode = str(mode or "auto").lower()
    if selected_mode == "no_llm":
        result = fallback
    elif circuit_status().get("open"):
        result = {**fallback, "source": "no_llm_circuit_open", "circuit": circuit_status()}
    else:
        try:
            result = _llm_package(title, summary, video_url)
        except QuotaError as exc:
            state = record_quota_failure(exc)
            result = {**fallback, "source": "no_llm_quota_fallback", "circuit": {**state, "open": True}}
        except Exception as exc:
            if selected_mode == "llm":
                raise RuntimeError(sanitize_error(exc)) from exc
            result = {**fallback, "source": "no_llm_error_fallback", "fallback_reason": sanitize_error(exc)}
    if component:
        if component not in fallback:
            raise ValueError("Unknown content component")
        return {component: result.get(component) or fallback[component], "source": result.get("source")}
    return result


def enqueue_content_package(*, clip_filename, title, summary="", video_url="", mode="auto", post_ids=None,
                            components=None, article_url="", create_website_article=False):
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        item = {
            "id": f"content_{int(time.time())}_{uuid.uuid4().hex[:8]}",
            "clip_filename": str(clip_filename or "").strip(),
            "title": str(title or ""),
            "summary": str(summary or ""),
            "video_url": str(video_url or ""),
            "mode": mode if mode in ("auto", "llm", "no_llm") else "auto",
            "components": components or ["hero_title", "article_html", "first_comment", "caption"],
            "post_ids": list(post_ids or []),
            "article_url": str(article_url or ""),
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
    output["website_link"] = {
        "status": str(item.get("website_status") or ("ready" if article_url else "not_configured")),
        "present": bool(article_url),
        "value": article_url,
    }
    return output


def resolve_article_url(item):
    """Create the CMS article only when the queue item definitely needs one.

    The CMS is called from the background worker, never from schedule creation, so
    a slow or failing CMS can no longer drop an accepted Facebook schedule.
    """
    existing = str(item.get("article_url") or "").strip()
    if not item.get("create_website_article"):
        return existing, "ready" if existing else "not_configured", ""
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
    for post in posts:
        if post.get("id") not in wanted:
            continue
        post["content_package_id"] = item["id"]
        post["content_package_status"] = "ready"
        post["content_package_source"] = result.get("source")
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
        if result.get("first_comment"):
            post["first_comment"] = result["first_comment"]
            post["first_comment_status"] = "ready"
            post["first_comment_error"] = ""
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
    if component == "first_comment" and (not snapshot.get("create_website_article") or snapshot.get("website_status") != "ready" or not snapshot.get("article_url")):
        raise ValueError("First Comment requires a newly published CMS article with original video embed")
    result = generate_package(
        snapshot.get("title", ""), snapshot.get("summary", ""), snapshot.get("video_url", ""),
        mode=mode or snapshot.get("mode", "auto"), component=component,
        article_url=snapshot.get("article_url", ""),
    )
    with _LOCK:
        items = _read(QUEUE_FILE, [])
        item = next((entry for entry in items if entry.get("id") == package_id), None)
        if not item:
            return None
        merged = item.get("result") if isinstance(item.get("result"), dict) else {}
        merged[component] = result.get(component)
        merged["source"] = result.get("source", "unknown")
        item.update({"result": merged, "status": "ready", "error": "", "updated_at": _now()})
        _write(QUEUE_FILE, items)
    _apply_to_posts(item)
    return {"component": component, "package": merged, "item": item}


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
        article_url, website_status, website_error = resolve_article_url(item)
        item["article_url"] = article_url
        item["website_status"] = website_status
        item["website_error"] = website_error
        item["embed_status"] = "ready" if website_status == "ready" and article_url else "failed"
        # Generate the comment after the CMS URL is known so the persisted
        # first comment contains the exact website link shown in Post Management.
        if "first_comment" in (item.get("components") or ["first_comment"]) and (website_status != "ready" or not article_url):
            raise RuntimeError("First Comment requires a newly published CMS article with original video embed")
        result = generate_package(
            item["title"], item.get("summary", ""), item.get("video_url", ""),
            item.get("mode", "auto"), article_url=article_url,
        )
        if "first_comment" in (item.get("components") or ["first_comment"]):
            comment = str(result.get("first_comment") or "").strip()
            if not comment or article_url not in comment:
                result["first_comment"] = fallback_package(item["title"], item.get("summary", ""), article_url)["first_comment"]
            if not result.get("first_comment") or article_url not in result["first_comment"]:
                raise RuntimeError("First Comment không chứa đúng URL bài CMS mới")
        retryable = str(result.get("source") or "").startswith("no_llm_quota_fallback")
        item.update({"status": "retryable" if retryable else "ready", "result": result, "error": "" if not retryable else "LLM quota exhausted; sẽ tự retry khi quota khả dụng.", "completed_at": _now()})
        if not retryable:
            _apply_to_posts(item)
    except Exception as exc:
        item.update({"status": "retryable" if isinstance(exc, QuotaError) else "failed", "error": sanitize_error(exc), "completed_at": _now()})
    with _LOCK:
        latest = _read(QUEUE_FILE, [])
        for index, existing in enumerate(latest):
            if existing.get("id") == item.get("id"):
                latest[index] = item
                break
        _write(QUEUE_FILE, latest)
    return {"processed": 1, "item": item, "items": latest}


def _worker_loop():
    lease = ProcessLease("content-package-worker", DATA_ROOT, stale_after=120)
    if not lease.acquire():
        return
    try:
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
