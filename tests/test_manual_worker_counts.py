import threading
from unittest import mock

import pytest

from multi_pc.publishing_settings import save_publishing_settings, load_publishing_settings
from src import content_packages as packages


@pytest.mark.parametrize("count", [3, 5, 9, 17, 32])
def test_custom_counts_persist_and_reload(tmp_path, monkeypatch, count):
    monkeypatch.setattr(packages, "DATA_ROOT", tmp_path)
    assert save_publishing_settings(tmp_path, count)["posting_threads"] == count
    assert load_publishing_settings(tmp_path)["posting_threads"] == count
    assert packages.content_worker_settings(count) == {"workers": count, "max_workers": 32}
    assert packages.content_worker_settings()["workers"] == count


@pytest.mark.parametrize("value", [0, -1, 33, True, "6", 2.5])
def test_invalid_content_counts_preserve_the_previous_setting(tmp_path, monkeypatch, value):
    monkeypatch.setattr(packages, "DATA_ROOT", tmp_path)
    packages.content_worker_settings(6)
    with pytest.raises(ValueError):
        packages.content_worker_settings(value)
    assert packages.content_worker_settings()["workers"] == 6


def test_content_executor_can_start_six_tasks_but_honors_selected_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(packages, "DATA_ROOT", tmp_path)
    packages.content_worker_settings(6)
    gate = threading.Event()
    started = threading.Event()
    lock = threading.Lock()
    count = 0
    observed = []
    def task():
        nonlocal count
        with lock:
            count += 1
            if count == 6:
                started.set()
        assert gate.wait(3)
    class StopLoop(Exception):
        pass
    def finish_loop(_):
        started.wait(1)
        observed.append(count)
        gate.set()
        raise StopLoop()
    monkeypatch.setattr(packages, "ProcessLease", lambda *a, **k: mock.Mock(acquire=lambda: True))
    monkeypatch.setattr(packages, "recover_abandoned_packages", lambda: False)
    monkeypatch.setattr(packages, "list_packages", lambda: [{"status": "queued"}])
    monkeypatch.setattr(packages, "process_content_packages_once", task)
    monkeypatch.setattr(packages.time, "sleep", finish_loop)
    with pytest.raises(StopLoop):
        packages._worker_loop()
    assert observed == [6]


def test_worker_apis_reject_missing_and_fractional_values(tmp_path, monkeypatch):
    from web import app as api
    monkeypatch.setattr(api, "POSTS_FILE", tmp_path / "posts.json")
    monkeypatch.setattr(packages, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(api, "start_content_package_worker", lambda: None)
    client = api.app.test_client()
    for value in (3, 11, 32):
        assert client.put("/api/publishing/settings", json={"posting_threads": value}).status_code == 200
        assert client.get("/api/publishing/settings").get_json()["posting_threads"] == value
        assert client.put("/api/content-studio/workers", json={"workers": value}).status_code == 200
        assert client.get("/api/content-studio/workers").get_json()["worker"]["workers"] == value
    for value in (None, 0, True, 33, 4.5, "8"):
        assert client.put("/api/publishing/settings", json={"posting_threads": value}).status_code == 400
        assert client.put("/api/content-studio/workers", json={"workers": value}).status_code == 400
    assert client.get("/api/content-studio/workers").get_json()["worker"]["workers"] == 32
