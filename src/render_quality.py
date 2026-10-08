"""Check the actual video timeline and decoding before exposing a render."""
from pathlib import Path
import json
import subprocess

from src.media_validation import InvalidMedia, probe_video


def validate_render(path, expected_duration, *, decode=True):
    info = probe_video(path, allow_rendering=True)
    tolerance = max(0.35, expected_duration * 0.02)
    if abs(info["duration"] - expected_duration) > tolerance:
        raise InvalidMedia("Video xuất không đủ thời lượng đoạn cắt; cần render lại.")
    bundled = Path(__file__).resolve().parents[1] / "bin"
    ffprobe = str(bundled / "ffprobe.exe") if (bundled / "ffprobe.exe").exists() else "ffprobe"
    result = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                             "stream=duration,avg_frame_rate,nb_frames", "-of", "json", str(path)],
                            capture_output=True, text=True, timeout=30,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    stream = json.loads(result.stdout)["streams"][0]
    video_duration = float(stream.get("duration") or info["duration"])
    if abs(video_duration - expected_duration) > tolerance:
        raise InvalidMedia("Luồng hình kết thúc sớm hơn đoạn cắt; không đưa clip vào kho đăng.")
    numerator, denominator = stream.get("avg_frame_rate", "0/1").split("/")
    fps = float(numerator) / max(float(denominator), 1)
    frames = int(stream.get("nb_frames") or 0)
    if fps < 12 or (frames and frames < expected_duration * 12 - 2):
        raise InvalidMedia("Nhịp khung hình quá thấp; cần render lại trước khi đăng.")
    if decode:
        ffmpeg = str(bundled / "ffmpeg.exe") if (bundled / "ffmpeg.exe").exists() else "ffmpeg"
        decoded = subprocess.run([ffmpeg, "-v", "error", "-xerror", "-i", str(path),
                                  "-map", "0:v:0", "-map", "0:a?", "-f", "null", "-"],
                                 capture_output=True, timeout=max(120, int(expected_duration * 5)),
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if decoded.returncode:
            raise InvalidMedia("MP4 có lỗi giải mã hình/âm thanh; cần render lại.")
    return {**info, "video_duration": video_duration, "fps": fps, "quality_verified": True}


def seconds(value):
    if isinstance(value, str) and ":" in value:
        pieces = value.strip().split(":")
        if len(pieces) not in (2, 3):
            raise ValueError("Invalid timestamp")
        result = 0.0
        for index, piece in enumerate(pieces):
            number = float(piece)
            if number < 0 or (index and number >= 60):
                raise ValueError("Invalid timestamp component")
            result = result * 60 + number
        return result
    return float(value)
