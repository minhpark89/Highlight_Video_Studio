"""Stage group-selected video into the installation's canonical output directory."""
import hashlib
import os
from pathlib import Path
import tempfile


def selected_video(folder, selection):
    """Accept a direct child of the explicitly configured folder, never a substitute basename."""
    root = Path(folder).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Configured source is not a folder")
    raw = str(selection or "").strip()
    if not raw:
        raise ValueError("Video path is empty")
    path = Path(raw)
    # Absolute selections must spell the exact configured child, not merely
    # resolve to one after traversing a link or a '..' component.
    if path.is_absolute():
        if path.parent != root:
            raise ValueError("Video is not a direct child of the configured folder")
    elif path.name != raw or raw in (".", "..") or "/" in raw or "\\" in raw:
        raise ValueError("Video selection must be a direct filename")
    path = root / path.name
    if path.is_symlink() or not path.is_file() or path.resolve(strict=True).parent != root:
        raise ValueError("Selected video escapes the configured folder or is not a file")
    if path.suffix.lower() != ".mp4":
        raise ValueError("Only MP4 video files can be scheduled")
    return path


def source_identity(path):
    return str(path.resolve(strict=True))


def stage_video(source, output_dir):
    """Copy with SHA-256, publish by no-replace hard link, verify collisions.

    The temp file is inside output so the final link is atomic on the same volume.
    The source stat checks reject ordinary in-flight edits; the verified digest
    always describes the bytes actually staged, even if source changes later.
    """
    source = Path(source)
    output = Path(output_dir).resolve(strict=True)
    if not output.is_dir() or source.is_symlink() or not source.is_file():
        raise ValueError("Source or output folder is invalid")
    identity = source_identity(source)
    before = source.stat()
    digest = hashlib.sha256()
    temporary = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(source, flags), "rb") as reader, tempfile.NamedTemporaryFile(dir=output, prefix=".stage-", suffix=".tmp", delete=False) as writer:
            opened = os.fstat(reader.fileno())
            if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino) or source.is_symlink():
                raise ValueError("Source changed during staging")
            temporary = Path(writer.name)
            for chunk in iter(lambda: reader.read(1024 * 1024), b""):
                writer.write(chunk)
                digest.update(chunk)
            writer.flush()
            os.fsync(writer.fileno())
        after = source.stat()
        if source.is_symlink() or (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError("Source changed during staging")
        sha = digest.hexdigest()
        source_key = hashlib.sha256(os.path.normcase(identity).encode("utf-8")).hexdigest()[:16]
        name = f"source-{source_key}-{sha}{source.suffix.lower()}"
        target = output / name
        try:
            os.link(temporary, target)
        except FileExistsError:
            # Never overwrite a staged file, including a poisoned collision.
            if target.is_symlink() or not target.is_file():
                raise ValueError("Staged video name collision")
            with target.open("rb") as existing:
                check = hashlib.sha256()
                for chunk in iter(lambda: existing.read(1024 * 1024), b""):
                    check.update(chunk)
            if check.hexdigest() != sha:
                raise ValueError("Staged video name collision")
        return name, sha, identity
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
