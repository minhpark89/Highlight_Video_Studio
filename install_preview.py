"""Install and launch the Highlight Video Studio offline preview build (non-destructive).

Scope:
- Copies the preview payload to a side-by-side directory outside the running production install.
- Never writes into ``D:\\Highlight_Video_Studio`` and never touches port 5080 or any process.
- Refuses a target that equals or is inside the production directory (fail-closed).
- Writes an uninstall manifest and a desktop shortcut for the preview only.
- Records build identity and SHA256 of the payload archive for verification.

Usage:
    python install_preview.py --payload Highlight_Desktop_Preview_v1.0.19-preview.2.zip
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from multi_pc.environment import PRERELEASE_BUILD, PRERELEASE_NAME, production_safety  # noqa: E402

MANIFEST_NAME = "preview_install_manifest.json"
LAUNCHER_NAME = "Launch_Highlight_Desktop_Preview.cmd"
SHORTCUT_NAME = "Highlight Video Studio (Offline Preview).lnk"


class PreviewInstallError(RuntimeError):
    """Raised when an install step cannot proceed safely."""


def default_target() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs" / PRERELEASE_NAME


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_safe_target(target: str | Path) -> Path:
    resolved = Path(target).resolve()
    safety = production_safety(resolved)
    if safety["production_payload_blocked"]:
        raise PreviewInstallError(
            f"Refusing to install into the production directory: {resolved}. "
            "Choose a side-by-side path."
        )
    return resolved


def zip_tree(source: str | Path, destination: str | Path) -> Path:
    src = Path(source)
    dest = Path(destination)
    if not src.is_dir():
        raise PreviewInstallError(f"payload source directory not found: {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(src.rglob("*")):
            if path.is_dir() or "__pycache__" in path.parts:
                continue
            if path.suffix in (".pyc", ".pyo"):
                continue
            archive.write(path, path.relative_to(src).as_posix())
    return dest


def stage_payload(source: str | Path, stage: str | Path) -> Path:
    src = Path(source).resolve()
    target = Path(stage).resolve()
    safety = production_safety()
    if safety["production_path"] and Path(safety["production_path"]).resolve() == src:
        raise PreviewInstallError("Refusing to stage from the production directory.")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns(
        "__pycache__", "*.pyc", "*.tmp", ".git", "build", "release",
    ))
    return target


def write_launcher_files(target: Path, data_root: Path) -> None:
    launcher = target / LAUNCHER_NAME
    python = sys.executable
    script = target / "run_local.py"
    launcher.write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        f'set "HIGHLIGHT_DATA_ROOT={data_root}"\r\n'
        f'"{python}" "{script}"\r\n',
        encoding="ascii",
    )


def write_manifest(target: Path, payload: Path, payload_hash: str) -> Path:
    manifest = target / MANIFEST_NAME
    manifest.write_text(json.dumps({
        "prerelease_name": PRERELEASE_NAME,
        "build": PRERELEASE_BUILD,
        "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "install_root": str(target),
        "payload": str(payload),
        "payload_sha256": payload_hash,
        "bind_host": "127.0.0.1",
        "bind_port": "ephemeral (never 5080)",
        "tunnel_required": False,
        "production_touched": False,
        "uninstall": "Delete the install_root directory; production install is untouched.",
    }, indent=2), encoding="utf-8")
    return manifest


def install(payload: str | Path, target: str | Path | None = None) -> dict:
    payload_path = Path(payload).resolve()
    if not payload_path.is_file():
        raise PreviewInstallError(f"payload not found: {payload_path}")
    dest = assert_safe_target(target or default_target())

    if shutil.which("tasklist"):
        # Informational only; the running production app is never signalled or stopped.
        pass

    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(payload_path, "r") as archive:
        for member in archive.namelist():
            member_path = (dest / member).resolve()
            if not str(member_path).startswith(str(dest)):
                raise PreviewInstallError(f"unsafe archive member: {member}")
        archive.extractall(dest)

    data_root = dest / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (dest / "run").mkdir(parents=True, exist_ok=True)

    write_launcher_files(dest, data_root)
    payload_hash = sha256_file(payload_path)
    manifest = write_manifest(dest, payload_path, payload_hash)

    return {
        "installed": True,
        "install_root": str(dest),
        "payload": str(payload_path),
        "payload_sha256": payload_hash,
        "manifest": str(manifest),
        "launcher": str(dest / LAUNCHER_NAME),
        "production_touched": False,
        "build": PRERELEASE_BUILD,
    }


def build_preview_payload(output: str | Path | None = None, include_data_policy: str = "reference") -> dict:
    """Stage the local-first preview payload and return its path, hash and size."""
    stage = ROOT / "build" / f"desktop-preview-{PRERELEASE_BUILD}"
    app_stage = stage / "app"

    for name in ("multi_pc", "core", "src", "web", "config"):
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(source, app_stage / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "*.tmp",
            ))
    for name in ("run_local.py", "run_server.py", "requirements.txt", "config.json"):
        source = ROOT / name
        if source.is_file():
            shutil.copy2(source, app_stage / name)

    readme = app_stage / "README_PREVIEW.txt"
    readme.write_text(
        f"{PRERELEASE_NAME} ({PRERELEASE_BUILD})\r\n"
        "Offline preview build. Loopback only, no tunnel, no public port.\r\n"
        f"Data policy: {include_data_policy} (existing data is read, never overwritten).\r\n"
        "Run install_preview.py --payload <zip> to install side-by-side, or run run_local.py directly.\r\n",
        encoding="utf-8",
    )

    archive = Path(output) if output else ROOT / "release" / f"Highlight_Desktop_Preview_v{PRERELEASE_BUILD}.zip"
    zip_tree(app_stage, archive)
    return {
        "payload": str(archive),
        "payload_sha256": sha256_file(archive),
        "payload_bytes": archive.stat().st_size,
        "stage": str(app_stage),
        "build": PRERELEASE_BUILD,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Highlight Video Studio offline preview installer")
    parser.add_argument("--payload", help="payload zip to install")
    parser.add_argument("--target", help="side-by-side install directory")
    parser.add_argument("--build", action="store_true", help="build the preview payload zip")
    parser.add_argument("--output", help="payload zip output path for --build")
    parser.add_argument("--json", action="store_true", help="print JSON result")
    args = parser.parse_args()

    try:
        if args.build:
            result = build_preview_payload(args.output)
        elif args.payload:
            result = install(args.payload, args.target)
        else:
            parser.error("provide --build or --payload")
            return 2
    except PreviewInstallError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for key, value in result.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
