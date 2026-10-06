"""Prepare immutable installer/checksum/checkpoint assets from inspected bytes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE = Path(__file__).resolve().parents[3]
RELEASE = SOURCE / "release"
EVIDENCE = SOURCE / "checkpoints/evidence/v1.2.8"

def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()

def main():
    proof = json.loads((EVIDENCE / "installer_payload.json").read_text(encoding="utf-8-sig"))
    tests = json.loads((EVIDENCE / "offline_tests.json").read_text(encoding="utf-8"))
    js = json.loads((EVIDENCE / "javascript_syntax.json").read_text(encoding="utf-8"))
    installer = RELEASE / "Highlight_Desktop_Test_Setup_v1.2.8.exe"
    tag = subprocess.check_output(["git", "rev-parse", "v1.2.8^{commit}"], cwd=SOURCE, text=True).strip()
    installer_hash = digest(installer)
    assert proof["success"] and tests["success"] and js["success"]
    assert proof["source_identity"]["source_commit"] == tag and not proof["source_identity"]["source_dirty"]
    assert installer_hash == proof["sha256"] and installer.stat().st_size == proof["size"]
    checksum = RELEASE / "Highlight_Desktop_Test_Setup_v1.2.8.sha256"
    checksum.write_text(f"{installer_hash}  {installer.name}\n", encoding="utf-8")
    checkpoint = RELEASE / "CODEX_CHECKPOINT_v1.2.8.md"
    intro = ("# Standalone release checkpoint — v1.2.8\n\n"
             f"Prepared at {datetime.now(timezone.utc).isoformat()}. Source/tag: `{tag}`.\n\n"
             f"Installer: `{installer.name}`, {installer.stat().st_size} bytes; SHA256 `{installer_hash}`.\n\n"
             f"Offline verification: **{tests['summary']}**. JavaScript syntax checked; no live Meta/CMS writes or runtime modification.\n\n"
             "This asset is prepared before publication and is immutable after upload. For final publication state, read "
             "`checkpoints/evidence/v1.2.8/` and the latest checkpoint on branch `release/v1.2.8`.\n\n")
    sections = [intro, (SOURCE / "CHECKPOINT_V1_2_8_GROUP_SLOTS_LOADING_20261006.md").read_text(encoding="utf-8")]
    sections += ["\n\n# Appendix: Meta v24 backend documentation\n\n", (SOURCE / "docs/META_V24_BACKEND.md").read_text(encoding="utf-8")]
    sections += ["\n\n# Appendix: Offline evidence\n\n```json\n", json.dumps(tests, indent=2), "\n```\n```json\n", json.dumps(js, indent=2), "\n```\n"]
    checkpoint.write_text("".join(sections), encoding="utf-8")
    benchmark = json.loads((EVIDENCE / "views_benchmark.json").read_text(encoding="utf-8"))
    notes = ("## v1.2.8 — Đủ khung giờ nhóm và tải danh sách nhanh hơn\n\n"
        "- Sửa nhóm ba khung giờ nhưng cửa sổ lên lịch chỉ có hai bài/Page. Hiện đủ mọi giờ; xác nhận lưu đúng số bài đã chọn.\n"
        "- Khi sửa giờ/giãn cách nhóm, Daily plan tương lai cập nhật tương ứng; giữ số bài giới hạn đã chọn và lịch đã gán/Meta.\n"
        "- Danh sách nhóm hiện trước; số video cập nhật riêng theo thư mục. Không chờ đọc jobs hoặc tải cả kho clip.\n"
        "- Danh sách bài dùng revision cache không TTL, audit chỉ annotate các dòng đang xem; đổi filter/trang bỏ response cũ.\n"
        "- Giữ Graph v24.0, Content/CMS/embed/comment/fallback và MP4/claim safeguards v1.2.7.\n\n"
        f"Offline: **{tests['summary']}**; Chromium 7 checks / 0 JS errors. "
        f"Benchmark local queue ẩn {benchmark['queue_rows']} bài: backend list median "
        f"{benchmark['v127_list_response']['median_ms']}→{benchmark['v128_list_response']['median_ms']} ms. "
        "Số đo không bao gồm UI/media/network thật.\n\n"
        "Đóng app cũ rồi cài đúng thư mục đang dùng. Vào NEW → Lên lịch → chọn 3 bài/Page → xác nhận. "
        "Nâng cấp không tự thay lịch đang có. Checkpoint độc lập và docs Meta đính kèm.\n\n"
        f"SHA256 installer: `{installer_hash}`.\n")
    (RELEASE / "v1.2.8_release_notes.md").write_text(notes, encoding="utf-8")
    assets = [{"name": path.name, "size": path.stat().st_size, "sha256": digest(path)}
              for path in (installer, checksum, checkpoint)]
    report = {"success": True, "source_commit": tag, "prepared_at_utc": datetime.now(timezone.utc).isoformat(), "assets": assets}
    (EVIDENCE / "prepared_assets.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))

if __name__ == "__main__":
    main()
