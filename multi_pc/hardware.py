import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .security import canonical_json, token_digest


PROFILE_CACHE_VERSION = 1
ENCODER_PRIORITY = ("nvenc", "qsv", "amf", "cpu")


def _run(command: list[str], **kwargs):
    try:
        return subprocess.run(command, **kwargs)
    except (OSError, ValueError):
        return None


@dataclass
class GpuInfo:
    vendor: str = "unknown"
    model: str = "unknown"
    vram_mb: int = 0
    driver_version: str = ""


@dataclass
class HardwareReport:
    gpu: GpuInfo = field(default_factory=GpuInfo)
    cpu_logical_cores: int = 0
    cpu_physical_cores: int = 0
    ram_mb: int = 0
    disk_free_mb: int = 0
    disk_write_mbps: float = 0.0
    encoders: dict = field(default_factory=dict)
    fingerprints: dict = field(default_factory=dict)


def detect_gpu(command_runner=None) -> GpuInfo:
    runner = command_runner or (lambda command: _run(command, capture_output=True, text=True, timeout=20))
    result = runner([
        "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ])
    if not result or getattr(result, "returncode", 1) != 0:
        return GpuInfo()
    line = (result.stdout or "").strip().splitlines()
    if not line:
        return GpuInfo()
    parts = [part.strip() for part in line[0].split(",")]
    return GpuInfo(
        vendor="nvidia",
        model=parts[0] if parts else "unknown",
        vram_mb=int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
        driver_version=parts[2] if len(parts) > 2 else "",
    )


def probe_encoders(ffmpeg_bin: str, command_runner=None) -> dict:
    runner = command_runner or (lambda command: _run(command, capture_output=True, text=True, timeout=30))
    result = runner([ffmpeg_bin, "-hide_banner", "-encoders"])
    if not result or getattr(result, "returncode", 1) != 0:
        return {name: False for name in ENCODER_PRIORITY}
    text = result.stdout or ""
    return {
        "nvenc": "h264_nvenc" in text,
        "qsv": "h264_qsv" in text,
        "amf": "h264_amf" in text,
        "cpu": "libx264" in text,
    }


def _disk_write_mbps(temp_dir: Path, size_mb: int = 64) -> float:
    import time

    block = os.urandom(1024 * 1024)
    target = Path(temp_dir) / "highlight_disk_probe.tmp"
    try:
        start = time.perf_counter()
        with open(target, "wb") as handle:
            for _ in range(size_mb):
                handle.write(block)
            handle.flush()
            os.fsync(handle.fileno())
        elapsed = max(time.perf_counter() - start, 1e-6)
    except OSError:
        return 0.0
    finally:
        try:
            target.unlink()
        except OSError:
            pass
    return round(size_mb / elapsed, 1)


def collect_hardware_report(ffmpeg_bin="ffmpeg", temp_dir: Path | None = None, command_runner=None) -> HardwareReport:
    gpu = detect_gpu(command_runner=command_runner)
    logical = os.cpu_count() or 1
    physical = logical
    report = HardwareReport(
        gpu=gpu,
        cpu_logical_cores=logical,
        cpu_physical_cores=physical,
        ram_mb=_total_ram_mb(),
        encoders=probe_encoders(ffmpeg_bin, command_runner=command_runner),
    )
    if temp_dir:
        target = Path(temp_dir)
        target.mkdir(parents=True, exist_ok=True)
        try:
            report.disk_free_mb = shutil.disk_usage(str(target)).free // (1024 * 1024)
        except OSError:
            report.disk_free_mb = 0
        report.disk_write_mbps = _disk_write_mbps(target)
    report.fingerprints = {
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "gpu_key": f"{gpu.vendor}:{gpu.model}:{gpu.driver_version}",
        "hardware_key": f"{gpu.vendor}:{gpu.model}:{report.cpu_logical_cores}:{report.ram_mb}",
    }
    return report


def _total_ram_mb() -> int:
    try:
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_phys", ctypes.c_ulonglong),
                ("avail_phys", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("avail_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("avail_virtual", ctypes.c_ulonglong),
                ("avail_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.total_phys // (1024 * 1024))
    except (AttributeError, OSError, ValueError):
        pass
    pages = os.sysconf("SC_PHYS_PAGES") if hasattr(os, "sysconf") else 0
    size = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 0
    return int(pages * size // (1024 * 1024)) if pages and size else 0


def canary_probe(encoder: str, ffmpeg_bin: str, temp_dir: Path, command_runner=None) -> bool:
    """Run one tiny synthetic encode. Device/marketing names alone are not trusted."""
    runner = command_runner or (lambda command: _run(command, capture_output=True, text=True, timeout=90))
    codec = {"nvenc": "h264_nvenc", "qsv": "h264_qsv", "amf": "h264_amf", "cpu": "libx264"}[encoder]
    output = Path(temp_dir) / f"highlight_canary_{encoder}.mp4"
    command = [
        ffmpeg_bin,
        "-hide_banner",
        "-loglevel", "error",
        "-f", "lavfi",
        "-i", "testsrc=size=640x360:rate=25:duration=1",
        "-c:v", codec,
        "-pix_fmt", "yuv420p",
        "-y",
        str(output),
    ]
    result = runner(command)
    produced = bool(result) and getattr(result, "returncode", 1) == 0 and output.is_file() and output.stat().st_size > 0
    try:
        output.unlink()
    except OSError:
        pass
    return produced


def derive_render_profile(report: HardwareReport, canary_results: dict | None = None) -> dict:
    canary_results = canary_results or {}

    def verified(encoder: str) -> bool:
        if encoder == "cpu":
            return True
        return bool(report.encoders.get(encoder)) and bool(canary_results.get(encoder))

    encoder = next((name for name in ENCODER_PRIORITY if verified(name)), "cpu")
    heavy = report.cpu_logical_cores >= 8 and report.ram_mb >= 16 * 1024
    moderate = report.cpu_logical_cores >= 4 and report.ram_mb >= 8 * 1024
    concurrency = 1 if encoder == "cpu" or not heavy else min(2, max(1, report.cpu_logical_cores // 4))
    profile = {
        "profile_version": PROFILE_CACHE_VERSION,
        "encoder": encoder,
        "encoder_label": {
            "nvenc": "nvidia-nvenc",
            "qsv": "intel-qsv",
            "amf": "amd-amf",
            "cpu": "cpu-libx264",
        }[encoder],
        "concurrency": concurrency,
        "max_concurrent_renders": concurrency,
        "hardware_decode": encoder in ("nvenc", "qsv", "amf"),
        "ram_budget_mb": int(report.ram_mb * 0.6) if report.ram_mb else 0,
        "notes": [],
    }
    if encoder == "cpu":
        profile["notes"].append("No verified hardware encoder; CPU fallback with bounded concurrency.")
    if report.ram_mb and report.ram_mb < 8 * 1024:
        profile["concurrency"] = 1
        profile["max_concurrent_renders"] = 1
        profile["notes"].append("Low RAM detected; renders serialized.")
    if not moderate:
        profile["notes"].append("Below recommended CPU/RAM baseline; expect slower renders.")
    if report.disk_free_mb and report.disk_free_mb < 20 * 1024:
        profile["notes"].append("Low free disk space; purge/rotate outputs before large jobs.")
    return profile
