"""Prepare immutable installer/checksum/checkpoint assets from inspected bytes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE = Path(__file__).resolve().parents[3]
RELEASE = SOURCE / "release"
EVIDENCE = SOURCE / "checkpoints/evidence/v1.2.7"

def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()

def main():
    proof = json.loads((EVIDENCE / "installer_payload.json").read_text(encoding="utf-8-sig"))
    tests = json.loads((EVIDENCE / "offline_tests.json").read_text(encoding="utf-8"))
    js = json.loads((EVIDENCE / "javascript_syntax.json").read_text(encoding="utf-8"))
    installer = RELEASE / "Highlight_Desktop_Test_Setup_v1.2.7.exe"
    tag = subprocess.check_output(["git", "rev-parse", "v1.2.7^{commit}"], cwd=SOURCE, text=True).strip()
    installer_hash = digest(installer)
    assert proof["success"] and tests["success"] and js["success"]
    assert proof["source_identity"]["source_commit"] == tag and not proof["source_identity"]["source_dirty"]
    assert installer_hash == proof["sha256"] and installer.stat().st_size == proof["size"]
    checksum = RELEASE / "Highlight_Desktop_Test_Setup_v1.2.7.sha256"
    checksum.write_text(f"{installer_hash}  {installer.name}\n", encoding="utf-8")
    checkpoint = RELEASE / "CODEX_CHECKPOINT_v1.2.7.md"
    intro = ("# Standalone release checkpoint — v1.2.7\n\n"
             f"Prepared at {datetime.now(timezone.utc).isoformat()}. Source/tag: `{tag}`.\n\n"
             f"Installer: `{installer.name}`, {installer.stat().st_size} bytes; SHA256 `{installer_hash}`.\n\n"
             f"Offline verification: **{tests['summary']}**. JavaScript syntax checked; no live Meta/CMS writes or runtime modification.\n\n"
             "This asset is prepared before publication and is immutable after upload. For final publication state, read "
             "`checkpoints/evidence/v1.2.7/` and the latest checkpoint on branch `release/v1.2.7`.\n\n")
    sections = [intro, (SOURCE / "CHECKPOINT_V1_2_7_MEDIA_CMS_RECOVERY_20261006.md").read_text(encoding="utf-8")]
    sections += ["\n\n# Appendix: Meta v24 backend documentation\n\n", (SOURCE / "docs/META_V24_BACKEND.md").read_text(encoding="utf-8")]
    sections += ["\n\n# Appendix: Offline evidence\n\n```json\n", json.dumps(tests, indent=2), "\n```\n```json\n", json.dumps(js, indent=2), "\n```\n"]
    checkpoint.write_text("".join(sections), encoding="utf-8")
    notes = ("## v1.2.7 — Sửa Public CMS và chọn MP4 phục hồi\n\n"
        "- Sửa nhận diện nhầm heading tiếng Anh làm bài Website đã có vẫn bị chặn; xác minh lại trước khi ép LLM tạo lại.\n"
        "- Đăng lại MP4: chọn clip kho đã FFprobe/hash/source/claim kiểm tra, xem thời lượng/nguồn/preview và lý do không dùng được.\n"
        "- Nếu kho không phù hợp, render nền từ video gốc, kiểm tra duration/mốc cắt thật, có tiến độ và xem trước. Render không tự đăng.\n"
        "- Khi đổi video, chuẩn bị Content, Website có embed nguồn và First Comment đúng link trước khi upload; giữ audit/Meta ID lỗi cũ, chống duplicate và restart.\n"
        "- Giữ Graph v24.0 và LLM/image ưu tiên với fallback v1.2.6.\n\n"
        f"Offline: **{tests['summary']}**; Chromium UI 5 checks / 0 JS errors; replay 4 public CMS bài bị lỗi đã qua kiểm tra mới. Chưa cài/sửa runtime đang dùng hoặc gọi publish/delete Meta/CMS thật.\n\n"
        "Đóng app cũ rồi cài đúng thư mục đang dùng. Lỗi CMS: **Thử lại Website**. Lỗi MP4: **Kiểm tra Meta → Đăng lại MP4 → chọn clip / render lại → xem trước → tạo lịch**. App chuẩn bị đủ Content trước khi đăng.\n\n"
        f"SHA256 installer: `{installer_hash}`. Checkpoint độc lập và docs Meta đính kèm.\n")
    (RELEASE / "v1.2.7_release_notes.md").write_text(notes, encoding="utf-8")
    assets = [{"name": path.name, "size": path.stat().st_size, "sha256": digest(path)}
              for path in (installer, checksum, checkpoint)]
    report = {"success": True, "source_commit": tag, "prepared_at_utc": datetime.now(timezone.utc).isoformat(), "assets": assets}
    (EVIDENCE / "prepared_assets.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))

if __name__ == "__main__":
    main()
