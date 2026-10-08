"""Transcribe bounded PCM chunks and retain completed chunks across retries."""
from pathlib import Path
import hashlib
import json
import math
import subprocess
import tempfile
import threading
import uuid

CHUNK_SECONDS = 300
INFERENCE_LOCK = threading.RLock()


def transcribe(audio_path, pipeline, progress=None):
    source = Path(audio_path)
    inspected = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "json", str(source)], capture_output=True, text=True,
                               timeout=30, creationflags=pipeline.NO_WINDOW)
    duration = float(json.loads(inspected.stdout)["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Audio không có thời lượng hợp lệ.")
    stat = source.stat()
    model = pipeline.get_whisper_model_source()
    identity = f"{source.resolve()}:{stat.st_size}:{stat.st_mtime_ns}:{model}:chunks-v1"
    key = hashlib.sha256(identity.encode()).hexdigest()[:24]
    cache = pipeline.TEMP_DIR / "transcript_chunks" / key
    cache.mkdir(parents=True, exist_ok=True)
    results = []
    for start in range(0, int(duration + 0.999), CHUNK_SECONDS):
        target = cache / f"{start}.json"
        if progress:
            progress(f"Nhận diện lời thoại {start:.0f}/{duration:.0f} giây; xử lý từng đoạn để tiết kiệm RAM.")
        if target.exists():
            results.extend(json.loads(target.read_text(encoding="utf-8")))
            continue
        with tempfile.TemporaryDirectory(prefix="speech-", dir=pipeline.TEMP_DIR) as folder:
            pcm = Path(folder) / "chunk.wav"
            converted = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start),
                                        "-i", str(source), "-t", str(CHUNK_SECONDS), "-vn", "-ac", "1",
                                        "-ar", "16000", "-c:a", "pcm_s16le", str(pcm)],
                                       capture_output=True, timeout=120, creationflags=pipeline.NO_WINDOW)
            if converted.returncode:
                raise RuntimeError("Không tách được đoạn audio để nhận diện; kiểm tra file tải về.")
            segments, _ = pipeline._transcribe_whisper(str(pcm), progress, beam_size=1, word_timestamps=True)
            chunk = [{"start": s.start + start, "duration": s.end - s.start, "text": s.text.strip(),
                      "words": [{"word": w.word.strip(), "start": w.start + start, "end": w.end + start}
                                for w in (s.words or [])]} for s in segments]
        temporary = target.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temporary.write_text(json.dumps(chunk, ensure_ascii=False), encoding="utf-8")
        temporary.replace(target)
        results.extend(chunk)
    return results
