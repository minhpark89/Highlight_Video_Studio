"""Validate local render/upload inputs without contacting a publishing service."""
import json
import math
import subprocess
from pathlib import Path


class InvalidMedia(ValueError):
    pass


def probe_video(path, *, allow_rendering=False):
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0 or (".rendering." in path.name and not allow_rendering):
        raise InvalidMedia("Video chưa hoàn chỉnh hoặc không tồn tại; hãy render lại trước khi đăng.")
    before = path.stat()
    bundled = Path(__file__).resolve().parents[1] / "bin" / "ffprobe.exe"
    executable = str(bundled) if bundled.is_file() else "ffprobe"
    try:
        result = subprocess.run(
            [executable, "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,width,height,duration:stream_disposition=attached_pic",
             "-of", "json", str(path)], capture_output=True, text=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        data = json.loads(result.stdout or "{}")
        streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"
                   and int(s.get("width") or 0) > 0 and int(s.get("height") or 0) > 0
                   and not (s.get("disposition") or {}).get("attached_pic")]
        duration = float(data.get("format", {}).get("duration") or
                         (streams[0].get("duration") if streams else 0) or 0)
        if result.returncode or not streams or not math.isfinite(duration) or duration <= 0:
            raise InvalidMedia("MP4 hỏng hoặc không có luồng video/thời lượng hợp lệ; hãy render lại trước khi đăng.")
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise InvalidMedia("Video còn đang được ghi; chờ render hoàn tất trước khi đăng.")
        return {"duration": duration, "size": after.st_size, "width": streams[0]["width"],
                "height": streams[0]["height"]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InvalidMedia("Chưa kiểm tra được video bằng ffprobe; kiểm tra bộ FFmpeg rồi thử lại.") from exc
    except (ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, InvalidMedia):
            raise
        raise InvalidMedia("MP4 không có dữ liệu video hợp lệ; hãy render lại trước khi đăng.") from exc


def valid_video(path):
    try:
        probe_video(path)
        return True
    except InvalidMedia:
        return False
