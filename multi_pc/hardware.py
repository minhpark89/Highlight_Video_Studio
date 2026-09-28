import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


PROFILE_CACHE_VERSION = 2
ENCODER_PRIORITY = ("nvenc", "qsv", "amf", "cpu")
ENCODER_CODECS = {
    "nvenc": "h264_nvenc",
    "qsv": "h264_qsv",
    "amf": "h264_amf",
    "cpu": "libx264",
}


def _run(command: list[str], **kwargs):
    try:
        return subprocess.run(command, **kwargs)
    except (OSError, ValueError, subprocess.TimeoutExpired):
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
    cpu_model: str = "unknown"
    cpu_logical_cores: int = 0
    cpu_physical_cores: int = 0
    ram_mb: int = 0
    disk_free_mb: int = 0
    disk_write_mbps: float = 0.0
    encoders: dict = field(default_factory=dict)
    fingerprints: dict = field(default_factory=dict)


def _powershell_json(script: str, command_runner=None):
    runner = command_runner or (lambda command: _run(command, capture_output=True, text=True, timeout=20))
    result = runner(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])
    if not result or getattr(result, "returncode", 1) != 0:
        return None
    try:
        return json.loads((result.stdout or "").strip())
    except (TypeError, ValueError):
        return None


def detect_gpu(command_runner=None) -> GpuInfo:
    runner = command_runner or (lambda command: _run(command, capture_output=True, text=True, timeout=20))
    result = runner([
        "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ])
    if result and getattr(result, "returncode", 1) == 0:
        lines = (result.stdout or "").strip().splitlines()
        if lines:
            parts = [part.strip() for part in lines[0].split(",")]
            return GpuInfo(
                vendor="nvidia",
                model=parts[0] if parts else "unknown",
                vram_mb=int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
                driver_version=parts[2] if len(parts) > 2 else "",
            )

    if os.name == "nt" and command_runner is None:
        rows = _powershell_json(
            "@(Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion) | ConvertTo-Json -Compress",
        )
        if isinstance(rows, dict):
            rows = [rows]
        if isinstance(rows, list) and rows:
            # Prefer discrete vendors, then the first detected adapter.
            rows.sort(key=lambda row: 0 if any(v in str(row.get("Name", "")).lower() for v in ("nvidia", "amd", "radeon", "intel arc")) else 1)
            row = rows[0]
            model = str(row.get("Name") or "unknown")
            lower = model.lower()
            vendor = "nvidia" if "nvidia" in lower else "amd" if any(v in lower for v in ("amd", "radeon")) else "intel" if "intel" in lower else "unknown"
            try:
                vram_mb = int(row.get("AdapterRAM") or 0) // (1024 * 1024)
            except (TypeError, ValueError):
                vram_mb = 0
            return GpuInfo(vendor=vendor, model=model, vram_mb=vram_mb, driver_version=str(row.get("DriverVersion") or ""))
    return GpuInfo()


def _ffmpeg_version(ffmpeg_bin: str, command_runner=None) -> str:
    """Return the FFmpeg build string so an upgraded FFmpeg invalidates the profile cache."""
    runner = command_runner or (lambda command: _run(command, capture_output=True, text=True, timeout=20))
    result = runner([ffmpeg_bin, "-hide_banner", "-version"])
    if not result or getattr(result, "returncode", 1) != 0:
        return "unknown"
    first = ((result.stdout or "").strip().splitlines() or [""])[0]
    return first.strip() or "unknown"


def probe_encoders(ffmpeg_bin: str, command_runner=None) -> dict:
    runner = command_runner or (lambda command: _run(command, capture_output=True, text=True, timeout=30))
    result = runner([ffmpeg_bin, "-hide_banner", "-encoders"])
    if not result or getattr(result, "returncode", 1) != 0:
        return {name: False for name in ENCODER_PRIORITY}
    text = result.stdout or ""
    return {name: codec in text for name, codec in ENCODER_CODECS.items()}


def _disk_write_mbps(temp_dir: Path, size_mb: int = 32) -> float:
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


def _cpu_details() -> tuple[str, int]:
    model = platform.processor() or platform.machine() or "unknown"
    physical = os.cpu_count() or 1
    if os.name == "nt":
        rows = _powershell_json("@(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores) | ConvertTo-Json -Compress")
        if isinstance(rows, dict):
            rows = [rows]
        if isinstance(rows, list) and rows:
            names = [str(row.get("Name") or "").strip() for row in rows if row.get("Name")]
            if names:
                model = " / ".join(names)
            try:
                physical = sum(int(row.get("NumberOfCores") or 0) for row in rows) or physical
            except (TypeError, ValueError):
                pass
    return model, physical


def collect_hardware_report(ffmpeg_bin="ffmpeg", temp_dir: Path | None = None, command_runner=None) -> HardwareReport:
    gpu = detect_gpu(command_runner=command_runner)
    logical = os.cpu_count() or 1
    cpu_model, physical = _cpu_details() if command_runner is None else (platform.processor() or "unknown", logical)
    report = HardwareReport(
        gpu=gpu,
        cpu_model=cpu_model,
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
        "gpu_key": f"{gpu.vendor}:{gpu.model}:{gpu.vram_mb}:{gpu.driver_version}",
        "hardware_key": f"{cpu_model}:{physical}:{logical}:{report.ram_mb}",
        "ffmpeg_key": _ffmpeg_version(ffmpeg_bin, command_runner=command_runner),
    }
    return report


def aggregate_disk_space(paths: list[str | Path] | None = None) -> dict:
    """Report free/total disk space for the volumes a render actually writes to.

    A render needs the output, temp and download volumes; the smallest one is the real constraint.
    """
    candidates = [Path(p) for p in (paths or [])]
    if not candidates:
        candidates = [Path.cwd()]
    per_volume: dict[str, dict] = {}
    for candidate in candidates:
        try:
            resolved = candidate if candidate.exists() else candidate.parent
            probe = resolved if resolved.exists() else Path.cwd()
            usage = shutil.disk_usage(str(probe))
        except (OSError, ValueError):
            continue
        anchor = str(probe.anchor or probe)
        entry = per_volume.setdefault(anchor, {"path": str(probe), "free_mb": 0, "total_mb": 0})
        free_mb = usage.free // (1024 * 1024)
        total_mb = usage.total // (1024 * 1024)
        # Keep the tightest constraint per volume when several paths share it.
        entry["free_mb"] = free_mb if not entry["free_mb"] else min(entry["free_mb"], free_mb)
        entry["total_mb"] = max(entry["total_mb"], total_mb)
    if not per_volume:
        return {"volumes": {}, "min_free_mb": 0, "critical": True}
    min_free = min(entry["free_mb"] for entry in per_volume.values())
    return {
        "volumes": per_volume,
        "min_free_mb": min_free,
        "critical": min_free < 20 * 1024,
    }


def _total_ram_mb() -> int:
    try:
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong),
                ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong), ("avail_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong),
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


def canary_probe(encoder: str, ffmpeg_bin: str, ffprobe_bin: str, temp_dir: Path, command_runner=None, duration_seconds: float = 2.0) -> dict:
    """Encode a short real 1080p clip and validate the artifact with ffprobe."""
    runner = command_runner or (lambda command: _run(command, capture_output=True, text=True, timeout=120))
    codec = ENCODER_CODECS[encoder]
    output = Path(temp_dir) / f"highlight_canary_{encoder}.mp4"
    command = [
        ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-f", "lavfi",
        "-i", f"testsrc2=size=1920x1080:rate=30:duration={duration_seconds}",
        "-an", "-c:v", codec, "-pix_fmt", "yuv420p",
    ]
    if encoder == "cpu":
        command.extend(["-preset", "veryfast", "-crf", "23"])
    elif encoder == "nvenc":
        command.extend(["-preset", "p2", "-cq", "23"])
    elif encoder == "qsv":
        command.extend(["-preset", "veryfast", "-global_quality", "23"])
    elif encoder == "amf":
        command.extend(["-quality", "speed", "-qp_i", "23", "-qp_p", "23"])
    command.extend(["-movflags", "+faststart", "-y", str(output)])

    started = time.perf_counter()
    result = runner(command)
    elapsed = round(time.perf_counter() - started, 3)
    entry = {
        "encoder": encoder,
        "codec": codec,
        "success": False,
        "elapsed_seconds": elapsed,
        "clip_seconds": duration_seconds,
        "realtime_factor": round(duration_seconds / elapsed, 2) if elapsed > 0 else 0.0,
        "output_bytes": output.stat().st_size if output.is_file() else 0,
        "width": 0,
        "height": 0,
        "frames": 0,
        "error": "",
    }
    if not result or getattr(result, "returncode", 1) != 0 or not output.is_file() or output.stat().st_size <= 0:
        entry["error"] = ((getattr(result, "stderr", "") or "encoder failed")[-800:]).strip()
    else:
        probe = runner([
            ffprobe_bin, "-v", "error", "-select_streams", "v:0",
            "-count_frames", "-show_entries", "stream=codec_name,width,height,nb_read_frames,duration",
            "-of", "json", str(output),
        ])
        if probe and getattr(probe, "returncode", 1) == 0:
            try:
                stream = (json.loads(probe.stdout or "{}").get("streams") or [{}])[0]
                entry["width"] = int(stream.get("width") or 0)
                entry["height"] = int(stream.get("height") or 0)
                entry["frames"] = int(stream.get("nb_read_frames") or 0)
                entry["success"] = entry["width"] == 1920 and entry["height"] == 1080 and entry["frames"] > 0
                if not entry["success"]:
                    entry["error"] = "ffprobe validation did not confirm a decodable 1920x1080 video stream"
            except (ValueError, TypeError, IndexError):
                entry["error"] = "ffprobe returned invalid JSON"
        else:
            entry["error"] = ((getattr(probe, "stderr", "") or "ffprobe failed")[-800:]).strip()
    try:
        output.unlink()
    except OSError:
        pass
    return entry


def run_encoder_canaries(report: HardwareReport, ffmpeg_bin: str, ffprobe_bin: str, temp_dir: Path, command_runner=None) -> dict:
    results = {}
    for encoder in ENCODER_PRIORITY:
        if report.encoders.get(encoder):
            results[encoder] = canary_probe(encoder, ffmpeg_bin, ffprobe_bin, temp_dir, command_runner=command_runner)
        else:
            results[encoder] = {"encoder": encoder, "codec": ENCODER_CODECS[encoder], "success": False, "error": "encoder not present in FFmpeg build"}
    return results


def benchmark_encoders(report: HardwareReport, ffmpeg_bin: str, ffprobe_bin: str, temp_dir: Path,
                       command_runner=None) -> dict:
    """Run real canary encodes and select the fastest encoder that produced a valid 1080p clip.

    Returns ``{encoder, codec, verified, selected, chosen_by, results}``. A candidate counts only
    when FFmpeg exits 0 and ffprobe confirms a decodable 1920x1080 stream, so a device name or a
    codec listed in ``-encoders`` is never enough on its own.

    Selection policy is deliberately conservative:
    - If a **verified hardware** encoder exists, the fastest verified hardware encoder wins
      (NVENC > QSV > AMF on ties), because the whole point of the probe is to use the GPU.
    - Otherwise CPU wins.
    - A hardware encoder is never accepted when it is slower than the CPU canary by a wide margin,
      since a GPU path that loses to libx264 is just extra failure surface.
    """
    results = run_encoder_canaries(report, ffmpeg_bin, ffprobe_bin, temp_dir, command_runner=command_runner)
    verified = [name for name in ENCODER_PRIORITY if (results.get(name) or {}).get("success")]
    hardware = [name for name in verified if name != "cpu"]

    chosen_by = "none"
    if hardware:
        fastest_hw = min(
            hardware,
            key=lambda name: (
                float((results.get(name) or {}).get("elapsed_seconds") or float("inf")),
                ENCODER_PRIORITY.index(name),
            ),
        )
        cpu_elapsed = float((results.get("cpu") or {}).get("elapsed_seconds") or 0.0)
        hw_elapsed = float((results.get(fastest_hw) or {}).get("elapsed_seconds") or 0.0)
        cpu_verified = bool((results.get("cpu") or {}).get("success"))
        if cpu_verified and cpu_elapsed > 0 and hw_elapsed > 0 and cpu_elapsed < hw_elapsed * 0.5:
            # CPU is more than 2x faster than the best working GPU path; prefer the proven CPU path.
            selected, chosen_by = "cpu", "cpu-faster-than-hardware"
        else:
            selected, chosen_by = fastest_hw, "fastest-verified-hardware"
    elif verified:
        selected, chosen_by = "cpu", "only-verified-encoder"
    else:
        selected, chosen_by = "cpu", "no-verified-encoder"

    winner = results.get(selected) or {}
    return {
        "encoder": selected,
        "codec": ENCODER_CODECS[selected],
        "verified": bool(winner.get("success")),
        "selected": selected,
        "chosen_by": chosen_by,
        "verified_encoders": verified,
        "results": results,
    }


def derive_render_profile(report: HardwareReport, canary_results: dict | None = None) -> dict:
    canary_results = canary_results or {}

    def verified(encoder: str) -> bool:
        result = canary_results.get(encoder)
        if isinstance(result, dict):
            result = result.get("success")
        return bool(report.encoders.get(encoder)) and bool(result)

    encoder = next((name for name in ENCODER_PRIORITY if verified(name)), "cpu")
    if canary_results.get("encoder") and canary_results.get("verified"):
        # The measured canary already proved which encoder actually works; trust the measurement
        # over the static probe list so a working NVENC/QSV/AMF result is never demoted.
        encoder = canary_results["encoder"]
    heavy = report.cpu_logical_cores >= 8 and report.ram_mb >= 16 * 1024
    moderate = report.cpu_logical_cores >= 4 and report.ram_mb >= 8 * 1024
    concurrency = 1 if encoder == "cpu" or not heavy else min(2, max(1, report.cpu_logical_cores // 8))
    profile = {
        "profile_version": PROFILE_CACHE_VERSION,
        "encoder": encoder,
        "codec": ENCODER_CODECS[encoder],
        "encoder_label": {"nvenc": "nvidia-nvenc", "qsv": "intel-qsv", "amf": "amd-amf", "cpu": "cpu-libx264"}[encoder],
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
    measured = (canary_results.get("results") or {}).get(encoder)
    if isinstance(measured, dict) and measured.get("success"):
        profile["canary"] = {
            "encoder": encoder,
            "elapsed_seconds": measured.get("elapsed_seconds"),
            "realtime_factor": measured.get("realtime_factor"),
            "output_bytes": measured.get("output_bytes"),
            "width": measured.get("width"),
            "height": measured.get("height"),
            "frames": measured.get("frames"),
        }
        profile["notes"].append(
            f"Canary verified {encoder} at {measured.get('realtime_factor')}x realtime "
            f"({measured.get('elapsed_seconds')}s for {measured.get('clip_seconds')}s 1080p30)."
        )
    if canary_results.get("chosen_by"):
        profile["chosen_by"] = canary_results["chosen_by"]
    return profile


def report_to_dict(report: HardwareReport) -> dict:
    return asdict(report)
