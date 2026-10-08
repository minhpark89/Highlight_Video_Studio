"""Attach already verified stock Content without restarting its CMS job."""
import copy


def attach_ready_package(packages, replacement, source):
    from src.video_recovery_media import reusable_content

    with packages._LOCK:
        rows = packages._read(packages.QUEUE_FILE, [])
        item = next((row for row in rows if row.get("id") == replacement["recovery_reuse_package_id"]), None)
        ready = reusable_content(replacement["media_file"], replacement["source_sha256"],
                                 source, [item] if item else [])
        if not ready or ready.get("website_video_status") != "youtube_embed_verified":
            raise ValueError("Content hoặc video nhúng chưa được xác minh; kiểm tra Website trước khi đăng.")
        item["post_ids"] = list(dict.fromkeys([*(item.get("post_ids") or []), replacement["id"]]))
        packages._write(packages.QUEUE_FILE, rows)
        return copy.deepcopy(item)
