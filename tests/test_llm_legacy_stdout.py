"""Regression coverage for the desktop launcher's redirected Windows stdout."""

import io
from unittest import mock

from src import pipeline


def test_llm_failure_preserves_fallback_when_stdout_uses_legacy_codepage():
    transcript = [
        {"start": float(second), "duration": 5.0, "text": "Cứ thử lại"}
        for second in range(0, 600, 10)
    ]
    raw = io.BytesIO()
    legacy_stdout = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    failure = RuntimeError("Không thể xử lý chữ ứ")
    with mock.patch.object(pipeline.requests, "post", side_effect=failure), mock.patch(
        "sys.stdout", legacy_stdout
    ):
        clips = pipeline.ask_llm_for_highlights(transcript, num_clips=3)
    legacy_stdout.flush()
    assert len(clips) == 3
    assert all(clip["end"] > clip["start"] for clip in clips)
    logged = raw.getvalue().decode("cp1252")
    assert "[LLM Error]" in logged
    assert "\\u1ee9" in logged


def test_llm_failure_keeps_fallback_when_log_stream_is_unavailable():
    transcript = [{"start": float(second), "duration": 5.0, "text": "line"} for second in range(0, 600, 10)]
    with mock.patch.object(pipeline.requests, "post", side_effect=RuntimeError("failed")), mock.patch(
        "builtins.print", side_effect=OSError("stream closed")
    ):
        clips = pipeline.ask_llm_for_highlights(transcript, num_clips=2)
    assert len(clips) == 2
