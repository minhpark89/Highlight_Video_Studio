from pathlib import Path

import pytest

from multi_pc.concurrency import (
    HARD_MAX_CONCURRENT_RENDERS,
    bounded_concurrency,
    resolve_concurrency,
)

ROOT = Path(__file__).resolve().parents[1]


def test_auto_preserves_profile_recommendation():
    assert resolve_concurrency("auto", None, 2) == ("auto", 2)


def test_manual_is_bounded_to_safe_limit():
    assert resolve_concurrency("manual", 4, 2) == ("manual", 4)
    with pytest.raises(ValueError):
        resolve_concurrency("manual", HARD_MAX_CONCURRENT_RENDERS + 1, 2)
    with pytest.raises(ValueError):
        resolve_concurrency("manual", 0, 2)


def test_invalid_mode_and_values_fail_closed():
    with pytest.raises(ValueError):
        resolve_concurrency("unsafe", 2, 2)
    with pytest.raises(ValueError):
        bounded_concurrency("not-a-number")


def test_queue_api_and_ui_keep_the_same_hard_bound_and_mirror():
    app_text = (ROOT / "web" / "app.py").read_text(encoding="utf-8")
    template = (ROOT / "web" / "templates" / "index.html").read_text(encoding="utf-8")
    served = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "HARD_MAX_CONCURRENT_RENDERS" in app_text
    assert 'max="4"' in template
    assert template == served
    assert "/api/queue/concurrency" in app_text
    assert "/api/queue/concurrency" in template
