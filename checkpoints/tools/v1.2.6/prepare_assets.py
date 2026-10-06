"""Prepare immutable installer/checksum/checkpoint assets from inspected bytes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE = Path(__file__).resolve().parents[3]
RELEASE = SOURCE / "release"
EVIDENCE = SOURCE / "checkpoints/evidence/v1.2.6"

def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()

def main():
    proof = json.loads((EVIDENCE / "installer_payload.json").read_text(encoding="utf-8-sig"))
    tests = json.loads((EVIDENCE / "offline_tests.json").read_text(encoding="utf-8"))
    js = json.loads((EVIDENCE / "javascript_syntax.json").read_text(encoding="utf-8"))
    installer = RELEASE / "Highlight_Desktop_Test_Setup_v1.2.6.exe"
    tag = subprocess.check_output(["git", "rev-parse", "v1.2.6^{commit}"], cwd=SOURCE, text=True).strip()
    installer_hash = digest(installer)
    assert proof["success"] and tests["success"] and js["success"]
    assert proof["source_identity"]["source_commit"] == tag and not proof["source_identity"]["source_dirty"]
    assert installer_hash == proof["sha256"] and installer.stat().st_size == proof["size"]
    checksum = RELEASE / "Highlight_Desktop_Test_Setup_v1.2.6.sha256"
    checksum.write_text(f"{installer_hash}  {installer.name}\n", encoding="utf-8")
    checkpoint = RELEASE / "CODEX_CHECKPOINT_v1.2.6.md"
    intro = ("# Standalone release checkpoint — v1.2.6\n\n"
             f"Prepared at {datetime.now(timezone.utc).isoformat()}. Source/tag: `{tag}`.\n\n"
             f"Installer: `{installer.name}`, {installer.stat().st_size} bytes; SHA256 `{installer_hash}`.\n\n"
             f"Offline verification: **{tests['summary']}**. JavaScript syntax checked; no live Meta/CMS writes or runtime modification.\n\n"
             "This asset is prepared before publication and is immutable after upload. For final publication state, read "
             "`checkpoints/evidence/v1.2.6/` and the latest checkpoint on branch `release/v1.2.6`.\n\n")
    sections = [intro, (SOURCE / "CHECKPOINT_V1_2_6_CONTENT_RECOVERY_20261006.md").read_text(encoding="utf-8")]
    sections += ["\n\n# Appendix: Meta v24 backend documentation\n\n", (SOURCE / "docs/META_V24_BACKEND.md").read_text(encoding="utf-8")]
    sections += ["\n\n# Appendix: Offline evidence\n\n```json\n", json.dumps(tests, indent=2), "\n```\n```json\n", json.dumps(js, indent=2), "\n```\n"]
    checkpoint.write_text("".join(sections), encoding="utf-8")
    notes = ("## v1.2.6 — Content fallback và phục hồi bài lỗi\n\n"
        "- Text LLM vẫn ưu tiên; lỗi/quota/JSON sai dùng nội dung fallback từ tiêu đề, mô tả và transcript nguồn, giữ form English 600+ từ.\n"
        "- Thumbnail ưu tiên model ảnh; ảnh minh họa lấy video dài gốc. Chấp nhận nguồn ngang 4:3, xuất frame 16:9; không dùng Reel dọc thay nguồn.\n"
        "- Bài Website có original video embed được xác minh; First Comment dùng đúng link Website. Thử lại giữ URL/CMS ID cũ, có retry trễ cho CMS429.\n"
        "- Bài processing được Meta xác nhận lỗi terminal có thể đăng lại MP4 qua App hoặc Meta giữ lịch; thùng rác local lưu audit và kiểm tra Meta mới trước khi xóa.\n"
        "- Graph API v24.0. Lỗi Meta 368/4854002 vẫn cần xử lý quyền/danh tính đúng Page.\n\n"
        f"Kiểm tra offline: **{tests['summary']}**; JavaScript syntax hợp lệ. Chưa cài vào runtime người dùng hoặc đăng/xóa Meta/CMS thật.\n\n"
        "Đóng app cũ rồi cài vào thư mục đang sử dụng. Sau mở lại, dùng **Thử lại Website** cho lỗi Content; "
        "dùng **Kiểm tra Meta** rồi **Đăng lại MP4** cho video lỗi được xác nhận. Bài scheduled/published/unknown giữ ID hiện có để tránh đăng trùng.\n\n"
        f"SHA256 installer: `{installer_hash}`. Checkpoint độc lập kèm docs Meta được đính kèm.\n")
    (RELEASE / "v1.2.6_release_notes.md").write_text(notes, encoding="utf-8")
    assets = [{"name": path.name, "size": path.stat().st_size, "sha256": digest(path)}
              for path in (installer, checksum, checkpoint)]
    report = {"success": True, "source_commit": tag, "prepared_at_utc": datetime.now(timezone.utc).isoformat(), "assets": assets}
    (EVIDENCE / "prepared_assets.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))

if __name__ == "__main__":
    main()
