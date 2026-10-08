"""Resume validated local downloads and use bounded network attempts."""
from pathlib import Path
import json
import subprocess
import time

from src.download_process import DownloadStalled, run_download
from src.job_store import load as load_jobs
from src.media_validation import probe_video


def _complete(path, expected=0):
    try:
        info = probe_video(path)
        if expected and abs(info["duration"] - expected) > max(3, expected * 0.002):
            return None
        # Validate the final frames too: a readable MP4 header is not proof that
        # a previously interrupted transfer contains the end of the source.
        tail = subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-sseof", "-3", "-i", str(path),
                               "-map", "0:v:0", "-f", "null", "-"], capture_output=True,
                              timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if tail.returncode:
            return None
        return info
    except (ValueError, OSError, subprocess.TimeoutExpired):
        return None


def _metadata(path):
    try:
        return json.loads(path.with_suffix(".info.json").read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def download(pipeline, url, job_id, progress=None):
    video = pipeline.DOWNLOADS_DIR / f"{job_id}.mp4"
    audio = pipeline.TEMP_DIR / f"{job_id}.mp3"
    pipeline.DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    pipeline.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    jobs = load_jobs(pipeline.DOWNLOADS_DIR.parent / "jobs.json")
    job = next((row for row in jobs if row.get("id") == job_id and row.get("youtube_url") == url), {})
    metadata = _metadata(video)
    expected = float(metadata.get("duration") or job.get("duration") or 0)
    complete = _complete(video, expected) if job or metadata.get("webpage_url") == url else None
    partial = any(video.parent.glob(video.stem + "*.part"))
    if complete and not partial:
        if progress:
            progress("Đã có video tải hoàn chỉnh; dùng lại file sau khi kiểm tra thời lượng.")
    else:
        complete, metadata = _download_attempts(pipeline, url, video, progress)
    _audio(pipeline, video, audio, complete["duration"], progress)
    return {"video_path": str(video), "audio_path": str(audio), "duration": complete["duration"],
            "title": metadata.get("title") or job.get("video_title") or "Video đã tải"}


def _download_attempts(pipeline, url, video, progress):
    credentials = [None]
    credentials.extend(("--cookies-from-browser", profile) for profile in pipeline._chrome_cookie_specs())
    if pipeline.COOKIES_FILE.is_file():
        credentials.append(("--cookies", str(pipeline.COOKIES_FILE)))
    last_error = "Không tải được video nguồn."
    for credential in credentials:
        for attempt in range(2):
            if progress:
                progress(f"Tải video nguồn, lần {attempt + 1}/2; tự tiếp tục phần đã tải.")
            command = [pipeline.YT_DLP_BIN, "--no-playlist", "--continue", "--newline", "--progress",
                       "--socket-timeout", "20", "--retries", "3", "--fragment-retries", "3",
                       "--extractor-retries", "2", "--retry-sleep", "2", "--concurrent-fragments", "4",
                       "--abort-on-unavailable-fragments", "--write-info-json",
                       "--progress-template", "download:__HVS_PROGRESS__ %(progress.downloaded_bytes)s",
                       "-f", "bv[vcodec^=avc1][height<=1080]+ba[ext=m4a]/bv[height<=1080]+ba/b[height<=1080]",
                       "--merge-output-format", "mp4", "--remux-video", "mp4", "-o", str(video)]
            if pipeline.NODE_BIN and Path(pipeline.NODE_BIN).exists():
                command.extend(["--js-runtimes", f"node:{pipeline.NODE_BIN}"])
            if credential:
                command.extend(credential)
            command.append(url)
            try:
                result = run_download(command, video, progress)
                last_error = result.stderr[-1800:]
                metadata = _metadata(video)
                complete = _complete(video, float(metadata.get("duration") or 0))
                if result.returncode == 0 and complete:
                    return complete, metadata
                # Do not repeatedly download a deleted/private source as though it were a network stall.
                if any(text in last_error.lower() for text in ("video unavailable", "video has been removed")):
                    raise ValueError("Video nguồn không còn truy cập được. Kiểm tra link hoặc thay nguồn.")
                if any(text in last_error.lower() for text in ("sign in", "403", "forbidden", "login", "bot")):
                    break
            except DownloadStalled as exc:
                last_error = str(exc)
                metadata = _metadata(video)
                complete = _complete(video, float(metadata.get("duration") or 0))
                if complete and not any(video.parent.glob(video.stem + "*.part")):
                    return complete, metadata
            time.sleep(attempt + 1)
    raise RuntimeError("Tải YouTube chưa hoàn tất. Kiểm tra mạng/đăng nhập rồi thử lại; phần tải được giữ. "
                       + last_error[-600:])


def _audio(pipeline, video, audio, duration, progress):
    if audio.is_file():
        checked = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                  "-of", "json", str(audio)], capture_output=True, text=True,
                                 timeout=30, creationflags=pipeline.NO_WINDOW)
        try:
            if abs(float(json.loads(checked.stdout)["format"]["duration"]) - duration) < 2:
                return
        except (ValueError, KeyError):
            pass
    if progress:
        progress("Đang tách audio từ file video đã kiểm tra.")
    temporary = audio.with_name(audio.stem + ".extracting.mp3")
    converted = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1",
                                "-ar", "16000", "-c:a", "libmp3lame", "-q:a", "2", str(temporary)],
                               capture_output=True, timeout=max(300, int(duration)), creationflags=pipeline.NO_WINDOW)
    if converted.returncode or not temporary.exists() or not temporary.stat().st_size:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("Không tách được audio; kiểm tra lại tính toàn vẹn của video nguồn.")
    temporary.replace(audio)
