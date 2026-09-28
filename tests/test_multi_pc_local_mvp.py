"""Tests for the local-first MVP: encoder canary, loopback launcher, offline environment report."""

import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from multi_pc import local_launcher as launcher  # noqa: E402
from multi_pc.hardware import HardwareReport, GpuInfo, derive_render_profile  # noqa: E402


# --- loopback launcher ------------------------------------------------------------------------

def test_non_loopback_bind_is_refused():
    for host in ("0.0.0.0", "192.168.1.10", "example.com", "::"):
        with pytest.raises(launcher.LoopbackBindError):
            launcher.assert_loopback(host)


def test_loopback_hosts_allowed():
    for host in ("127.0.0.1", "::1", "localhost"):
        assert launcher.assert_loopback(host) == host


def test_free_port_is_ephemeral_and_usable():
    port = launcher.pick_free_port()
    assert 1024 < port < 65536
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))


def test_port_5080_is_never_reused():
    with pytest.raises(launcher.LoopbackBindError):
        launcher.resolve_config(port=5080)


def test_resolve_config_defaults_to_ephemeral_loopback(tmp_path):
    config = launcher.resolve_config(runtime_dir=tmp_path)
    assert config["host"] == "127.0.0.1"
    assert isinstance(config["port"], int) and config["port"] != 5080


def test_session_guard_blocks_missing_and_bad_tokens():
    guard = launcher.SessionGuard("secret-token")
    assert guard.authorize({"REMOTE_ADDR": "127.0.0.1", "PATH_INFO": "/api/jobs"}) is False
    assert guard.authorize({"REMOTE_ADDR": "127.0.0.1", "PATH_INFO": "/api/jobs", "HTTP_X_HIGHLIGHT_SESSION": "wrong"}) is False
    assert guard.authorize({"REMOTE_ADDR": "127.0.0.1", "PATH_INFO": "/api/jobs", "HTTP_X_HIGHLIGHT_SESSION": "secret-token"}) is True


def test_session_guard_blocks_non_loopback_even_with_token():
    guard = launcher.SessionGuard("secret-token")
    assert guard.authorize({"REMOTE_ADDR": "10.0.0.5", "PATH_INFO": "/api/jobs", "HTTP_X_HIGHLIGHT_SESSION": "secret-token"}) is False


def test_session_guard_accepts_cookie_and_healthz_exempt():
    guard = launcher.SessionGuard("tok")
    assert guard.authorize({"REMOTE_ADDR": "127.0.0.1", "PATH_INFO": "/api/jobs", "HTTP_COOKIE": "a=1; highlight_session=tok"}) is True
    assert guard.authorize({"REMOTE_ADDR": "127.0.0.1", "PATH_INFO": "/healthz"}) is True


def test_wsgi_middleware_returns_401_without_token():
    guard = launcher.SessionGuard("tok")
    calls = []

    def inner(environ, start_response):
        calls.append(environ)
        start_response("200 OK", [])
        return [b"ok"]

    app = guard.wsgi_middleware(inner)
    statuses = []

    def capture(status, headers):
        statuses.append(status)

    body = app({"REMOTE_ADDR": "127.0.0.1", "PATH_INFO": "/api/jobs"}, capture)
    assert statuses == ["401 Unauthorized"]
    assert body == [b"unauthorized"]
    assert calls == []


def test_runtime_file_round_trip(tmp_path):
    config = launcher.resolve_config(runtime_dir=tmp_path)
    handle = launcher.build_handle(config, token="tok-123")
    path = handle.write_runtime_file()
    assert path.is_file()
    loaded = launcher.load_runtime_file(path)
    assert loaded["token"] == "tok-123"
    assert loaded["url"] == handle.url
    handle.remove_runtime_file()
    assert not path.exists()


def test_public_dict_hides_token_by_default(tmp_path):
    config = launcher.resolve_config(runtime_dir=tmp_path)
    handle = launcher.build_handle(config, token="tok-123")
    assert "token" not in handle.public_dict()
    assert handle.public_dict(include_token=True)["token"] == "tok-123"


def test_session_tokens_are_unique_and_long():
    tokens = {launcher.new_session_token() for _ in range(20)}
    assert len(tokens) == 20
    assert all(len(t) >= 32 for t in tokens)


# --- profile derivation from measured canary --------------------------------------------------

def _report(**overrides):
    base = dict(gpu=GpuInfo(vendor="nvidia", model="RTX 3060", vram_mb=12288, driver_version="610.88"),
                cpu_model="Xeon", cpu_logical_cores=56, cpu_physical_cores=28, ram_mb=98206,
                disk_free_mb=200000, encoders={"nvenc": True, "qsv": True, "amf": True, "cpu": True})
    base.update(overrides)
    return HardwareReport(**base)


def test_derived_profile_trusts_verified_canary_encoder():
    canary = {"encoder": "nvenc", "verified": True, "results": {"nvenc": {"encoder": "nvenc", "success": True, "elapsed_seconds": 0.5, "realtime_factor": 3.6, "output_bytes": 4096, "width": 1920, "height": 1080, "frames": 60, "clip_seconds": 2.0}}}
    profile = derive_render_profile(_report(), canary)
    assert profile["encoder"] == "nvenc"
    assert profile["hardware_decode"] is True
    assert profile["canary"]["realtime_factor"] == 3.6


def test_canary_failure_demotes_to_cpu():
    canary = {"encoder": "cpu", "verified": True, "results": {
        "nvenc": {"encoder": "nvenc", "success": False, "error": "no device"},
        "cpu": {"encoder": "cpu", "success": True, "elapsed_seconds": 0.4, "realtime_factor": 5.0, "output_bytes": 1024, "width": 1920, "height": 1080, "frames": 60, "clip_seconds": 2.0},
    }}
    profile = derive_render_profile(_report(encoders={"nvenc": True, "qsv": False, "amf": False, "cpu": True}), canary)
    assert profile["encoder"] == "cpu"
    assert profile["hardware_decode"] is False


def test_unverified_hardware_encoder_never_selected():
    canary = {"encoder": "nvenc", "verified": False, "results": {
        "nvenc": {"encoder": "nvenc", "success": False, "error": "fail"},
        "cpu": {"encoder": "cpu", "success": True, "elapsed_seconds": 0.4, "realtime_factor": 5.0, "output_bytes": 1024, "width": 1920, "height": 1080, "frames": 60, "clip_seconds": 2.0},
    }}
    profile = derive_render_profile(_report(), canary)
    assert profile["encoder"] == "cpu"


def test_low_ram_forces_single_concurrency():
    profile = derive_render_profile(_report(ram_mb=4096), {"encoder": "cpu", "verified": True, "results": {"cpu": {"success": True, "clip_seconds": 2.0}}})
    assert profile["concurrency"] == 1
    assert any("Low RAM" in note for note in profile["notes"])


# --- offline environment report / installer plan ----------------------------------------------

def test_production_safety_blocks_production_path():
    from multi_pc import environment as env

    blocked = env.production_safety(env.PRODUCTION_APP)
    assert blocked["production_payload_blocked"] is True
    assert blocked["touches_production"] is False


def test_production_safety_allows_side_by_side(tmp_path):
    from multi_pc import environment as env

    safe = env.production_safety(tmp_path / "HighlightDesktopPreview")
    assert safe["production_payload_blocked"] is False


def test_install_plan_is_side_by_side_and_local_only(tmp_path):
    from multi_pc import environment as env

    plan = env.install_plan(tmp_path / "HighlightDesktopPreview")
    assert plan["mode"] == "side-by-side"
    assert plan["bind_host"] == "127.0.0.1"
    assert plan["tunnel_required"] is False
    assert plan["inbound_port"] is None
    assert "5080" in plan["bind_port"]
    assert plan["preserves_existing_data"] is True


def test_prerelease_identity_differs_from_production_version():
    from multi_pc import environment as env

    assert env.PRERELEASE_BUILD.startswith("1.0.19-")
    assert env.PRERELEASE_BUILD != "1.0.19"
    assert "preview" in env.PRERELEASE_NAME


def test_environment_report_offline_and_json_serialisable():
    from multi_pc import environment as env

    report = env.environment_report(run_canary=False, force=True)
    assert report["production_safety"]["touches_production"] is False
    assert report["canary"] == {}
    assert report["build"] == env.PRERELEASE_BUILD
    json.dumps(report)


def test_find_ffmpeg_prefers_path_over_production():
    from multi_pc import environment as env

    resolved = env._find_ffmpeg()
    assert resolved
    assert "Highlight_Video_Studio" not in resolved or resolved.endswith("ffmpeg.exe")
