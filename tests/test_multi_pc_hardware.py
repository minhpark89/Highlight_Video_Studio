import json
import tempfile
import unittest
from pathlib import Path

from multi_pc.hardware import (
    ENCODER_PRIORITY,
    GpuInfo,
    HardwareReport,
    canary_probe,
    collect_hardware_report,
    derive_render_profile,
)
from multi_pc.profile_cache import ProfileCache


class FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def report(**overrides) -> HardwareReport:
    base = HardwareReport(
        gpu=GpuInfo(vendor="nvidia", model="RTX 3060", vram_mb=12288, driver_version="610.88"),
        cpu_model="Test CPU",
        cpu_logical_cores=16,
        cpu_physical_cores=8,
        ram_mb=32768,
        disk_free_mb=200000,
        disk_write_mbps=900.0,
        encoders={"nvenc": True, "qsv": False, "amf": False, "cpu": True},
        fingerprints={"gpu_key": "nvidia:RTX 3060:12288:610.88", "hardware_key": "h"},
    )
    base.__dict__.update(overrides)
    return base


class HardwareDetectionTests(unittest.TestCase):
    def test_prefers_verified_nvenc(self):
        profile = derive_render_profile(report(), canary_results={"nvenc": {"success": True}})
        self.assertEqual(profile["encoder"], "nvenc")
        self.assertEqual(profile["codec"], "h264_nvenc")
        self.assertTrue(profile["hardware_decode"])
        self.assertGreaterEqual(profile["max_concurrent_renders"], 1)

    def test_unverified_encoder_falls_back_in_priority_order(self):
        hardware = report(encoders={"nvenc": True, "qsv": True, "amf": False, "cpu": True})
        profile = derive_render_profile(hardware, canary_results={"nvenc": {"success": False}, "qsv": {"success": True}})
        self.assertEqual(profile["encoder"], "qsv")
        cpu_only = derive_render_profile(hardware, canary_results={"nvenc": False, "qsv": False, "cpu": True})
        self.assertEqual(cpu_only["encoder"], "cpu")
        self.assertEqual(cpu_only["concurrency"], 1)
        self.assertEqual(list(ENCODER_PRIORITY), ["nvenc", "qsv", "amf", "cpu"])

    def test_low_ram_and_disk_are_bounded(self):
        profile = derive_render_profile(
            report(cpu_logical_cores=2, ram_mb=4096, disk_free_mb=1024),
            canary_results={"encoder": "nvenc", "verified": True, "results": {"nvenc": {"success": True}}},
        )
        self.assertEqual(profile["encoder"], "nvenc")
        self.assertEqual(profile["max_concurrent_renders"], 1)
        self.assertTrue(any("RAM" in note for note in profile["notes"]))
        self.assertTrue(any("disk" in note.lower() for note in profile["notes"]))

    def test_detection_uses_tooling_not_device_marketing_names(self):
        commands = []

        def runner(command):
            commands.append(command)
            if command[0] == "nvidia-smi":
                return FakeCompleted(stdout="NVIDIA GeForce RTX 3060, 12288, 610.88\n")
            return FakeCompleted(stdout=" V....D h264_nvenc NVIDIA NVENC H.264 encoder\n V....D h264_qsv Intel QSV H.264 encoder\n V....D libx264 libx264 H.264\n")

        with tempfile.TemporaryDirectory() as folder:
            collected = collect_hardware_report(ffmpeg_bin="ffmpeg", temp_dir=Path(folder), command_runner=runner)
        self.assertEqual(collected.gpu.model, "NVIDIA GeForce RTX 3060")
        self.assertEqual(collected.gpu.vram_mb, 12288)
        self.assertTrue(collected.encoders["nvenc"])
        self.assertFalse(collected.encoders["amf"])
        self.assertIn("gpu_key", collected.fingerprints)

    def test_canary_is_1080p_and_ffprobe_validated(self):
        commands = []

        def runner(command):
            commands.append(command)
            output = Path(command[-1])
            if "ffprobe" in command[0]:
                return FakeCompleted(stdout=json.dumps({"streams": [{"width": 1920, "height": 1080, "nb_read_frames": "60"}]}))
            output.write_bytes(b"valid-video")
            return FakeCompleted()

        with tempfile.TemporaryDirectory() as folder:
            result = canary_probe("cpu", "ffmpeg", "ffprobe", Path(folder), command_runner=runner)
        self.assertTrue(result["success"])
        self.assertEqual((result["width"], result["height"]), (1920, 1080))
        self.assertEqual(result["frames"], 60)
        self.assertIn("testsrc2=size=1920x1080", " ".join(commands[0]))
        self.assertIn("-count_frames", commands[1])


class ProfileCacheTests(unittest.TestCase):
    def test_cache_reused_then_invalidated_on_driver_change(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = ProfileCache(Path(folder) / "hardware_profile.json")
            first = cache.resolve(report(), {"nvenc": {"success": True}})
            self.assertEqual(first["source"], "probe")
            cached = cache.resolve(report(), {"nvenc": {"success": True}})
            self.assertEqual(cached["source"], "cache")
            self.assertEqual(cached["encoder"], "nvenc")
            entry = cache.load()
            self.assertIn("hardware", entry)
            self.assertIn("canaries", entry)

            changed = report(fingerprints={"gpu_key": "nvidia:RTX 3060:12288:999.99", "hardware_key": "h2"})
            rescanned = cache.resolve(changed, {"nvenc": {"success": True}})
            self.assertEqual(rescanned["source"], "probe")
            self.assertEqual(cache.load()["fingerprints"], changed.fingerprints)

    def test_expired_cache_is_reprobed(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = ProfileCache(Path(folder) / "hardware_profile.json", ttl_seconds=1)
            cache.resolve(report(), {"nvenc": {"success": True}})
            self.assertFalse(cache.is_valid(cache.load(), report().fingerprints, now=10**12))


if __name__ == "__main__":
    unittest.main()
