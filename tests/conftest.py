"""Keep offline tests independent of continuous workers and saved app queues."""
import threading

import pytest


_start_thread = threading.Thread.start


def _start_test_thread(thread, *args, **kwargs):
    target = getattr(thread, "_target", None)
    identity = (getattr(target, "__module__", ""), getattr(target, "__name__", ""))
    if identity in {
        ("web.app", "queue_worker_loop"),
        ("web.scheduled_publisher", "scheduled_publisher_worker_loop"),
        ("src.content_packages", "_worker_loop"),
        ("src.output_pipeline", "_worker_loop"),
    }:
        return None
    # Concurrency tests still run their actual threads and executors.
    return _start_thread(thread, *args, **kwargs)


def pytest_sessionstart(session):
    threading.Thread.start = _start_test_thread


def pytest_sessionfinish(session, exitstatus):
    threading.Thread.start = _start_thread


@pytest.fixture(autouse=True)
def isolated_content_queue(tmp_path, monkeypatch):
    from src import content_packages

    monkeypatch.setattr(content_packages, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(content_packages, "QUEUE_FILE", tmp_path / "content_packages.json")
    monkeypatch.setattr(content_packages, "CIRCUIT_FILE", tmp_path / "llm_circuit.json")


@pytest.fixture(autouse=True)
def offline_original_transcripts(monkeypatch):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return
    def unavailable(*args, **kwargs):
        raise RuntimeError("Offline test: no source transcript fixture supplied")
    monkeypatch.setattr(YouTubeTranscriptApi, "fetch", unavailable)


@pytest.fixture(autouse=True)
def no_external_http_in_offline_tests(monkeypatch):
    import requests
    def blocked(self, method, url, **kwargs):
        raise requests.ConnectionError("Offline test: HTTP transport must be mocked")
    monkeypatch.setattr(requests.Session, "request", blocked)
