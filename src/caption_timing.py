"""Cache ASR on the exact decoded audio interval, independently of font/style."""
import hashlib
import json
import subprocess
import threading
import uuid
from pathlib import Path

from src.captions import normalize_words

_ALIGN_LOCK = threading.Lock()


def transcribe_slice(source, start, duration, pipeline, progress=None):
    path = Path(source).resolve()
    stat = path.stat()
    model = pipeline.get_whisper_model_source()
    identity = ["pcm-word-v2", str(path), stat.st_size, stat.st_mtime_ns,
                round(float(start), 6), round(float(duration), 6), str(model)]
    key = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
    directory = pipeline.TEMP_DIR / "caption_timing"
    directory.mkdir(parents=True, exist_ok=True)
    cache = directory / (key + ".json")
    with _ALIGN_LOCK:
        try:
            saved = json.loads(cache.read_text(encoding="utf-8"))
            words = normalize_words(saved["words"], duration)
            if words and saved.get("identity") == identity:
                if progress:
                    progress("Reusing cached speech word timestamps...")
                return words
        except (OSError, ValueError, KeyError, TypeError):
            pass
        audio = directory / (key + "." + uuid.uuid4().hex + ".wav")
        try:
            # MP3 stream-copy seeks are packet-aligned. Decode to PCM so word
            # time zero and the video's time zero refer to the exact same cut.
            command = ["ffmpeg", "-y", "-ss", str(start), "-i", str(path), "-t", str(duration),
                       "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio)]
            cut = subprocess.run(command, capture_output=True, timeout=120, creationflags=pipeline.NO_WINDOW)
            if cut.returncode != 0 or not audio.is_file() or audio.stat().st_size <= 44:
                raise RuntimeError("Cannot decode the selected audio interval for speech alignment")
            segments, _ = pipeline._transcribe_whisper(str(audio), progress, word_timestamps=True,
                beam_size=1, condition_on_previous_text=False, vad_filter=True)
            words = normalize_words([{"word": word.word.strip(), "start": word.start, "end": word.end}
                                     for segment in segments for word in (segment.words or [])], duration)
            if (path.stat().st_size, path.stat().st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
                raise RuntimeError("Source changed during speech alignment")
            if words:
                temporary = cache.with_suffix("." + uuid.uuid4().hex + ".tmp")
                try:
                    temporary.write_text(json.dumps({"identity": identity, "words": words}), encoding="utf-8")
                    temporary.replace(cache)
                finally:
                    temporary.unlink(missing_ok=True)
            return words
        finally:
            audio.unlink(missing_ok=True)
