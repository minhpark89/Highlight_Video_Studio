# Checkpoint mới nhất — Highlight Desktop Test v1.2.2

Ngày: 2026-10-06, Asia/Saigon. Xem [CHECKPOINT_V1_2_2_META_RECOVERY_20261006.md](CHECKPOINT_V1_2_2_META_RECOVERY_20261006.md).

Bản sửa thêm retry Init chắc chắn bị từ chối qua App, Sync Page/Token đọc lại Meta ID, cảnh báo lịch Meta quá giờ, chuyển cache text-only sang Website cho Daily và cách ly package non-English để pipeline tiếp tục. Full suite **608 passed, 4 skipped, 29 subtests passed**; browser offline **7 checks, không có JavaScript error**. Evidence: `checkpoints/evidence/v1.2.2/`.

Trạng thái hiện tại: đang chuẩn bị bộ cài/tag local trên `release/v1.2.2`. Kết nối GitHub qua shell bị chặn (`WinError 10013`); chưa push hoặc tạo release v1.2.2. Không coi link `releases/tag/v1.2.2` là đã có bản tải. Sau build, `installer_verify.json` ghi đúng source commit/hash; checkpoint này sẽ được cập nhật kết quả cuối. Giữ nguyên release/tag v1.2.1. Chưa cài vào runtime đang dùng hoặc đăng/xóa Meta/CMS thật.

Session sau đọc checkpoint v1.2.2 để lấy lệnh build/publish và cách xử lý từng loại lỗi; kiểm tra identity/PID/port, backup local trước nâng cấp, giữ Meta IDs/comment receipts/ledger. Bài `post_1791183298_90ab26` đã published; không đăng lại. Lỗi `368/4854002` vẫn cần xác minh Facebook.

## Bản phát hành trước — v1.2.1

Ngày: 2026-10-06 (Asia/Saigon). Nhánh phát hành: `release/v1.2.1`. Tag source: `v1.2.1` tại `edfdd753800c0171e5758b25b9da8a3b96766df3`.

Đọc [CHECKPOINT_V1_2_1_GROUP_REVIEW_20261006.md](CHECKPOINT_V1_2_1_GROUP_REVIEW_20261006.md): sửa nhận diện sai câu tiếng Anh làm Website/First Comment bị chặn; chuẩn bị và Draft theo nhóm có Page/Token/giờ; mặc định duyệt tay; giữ lịch Meta upload trước; phân trang 50/30 dòng; worker kho không ghi lại 800 bài khi không có thay đổi.

Kiểm thử: **581 passed, 3 skipped, 29 subtests passed**. Browser không có JavaScript error. Ba bài Website thực tế đã đọc lại HTTP 200 và xác minh English/YouTube gốc. Bộ cài local: `release/Highlight_Desktop_Test_Setup_v1.2.1.exe`; evidence mới ở `checkpoints/evidence/v1.2.1/`. Đã phát hành GitHub (Release ID `404026464`, `draft=false`, `prerelease=true`); ba asset, digest, tag và link tải không đăng nhập đã xác minh. Chưa cài đè runtime người dùng hoặc đăng/xóa bài Meta thật.

Release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.2.1. Checkpoint đính kèm: `CODEX_CHECKPOINT_v1.2.1.md`. Session sau đọc checkpoint trên nhánh phát hành, xác định identity/PID/port, sao lưu dữ liệu rồi retry đúng post/Website URL; giữ Meta IDs, comment receipt và ledger để tránh đăng trùng.

## Bản phát hành trước — v1.2.0

Ngày: 2026-10-05, Asia/Saigon. Nhánh: `release/v1.2.0`. Tag cố định: `v1.2.0`.

Đọc [CHECKPOINT_V1_2_0_20261005.md](CHECKPOINT_V1_2_0_20261005.md) trước khi sửa lỗi tiếp. Tài liệu ghi yêu cầu cuối cùng, nguyên nhân MP4 262 bytes, sửa Website cùng URL, quy trình tạo lịch thay thế, lệnh build/test và cách giữ dữ liệu/Meta IDs.

- Release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.2.0
- Installer: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.2.0/Highlight_Desktop_Test_Setup_v1.2.0.exe
- Full pytest: **567 passed, 3 skipped, 29 subtests passed**.
- Source đóng gói: `a199630d39d636e0c1b9173f12691cf2da1436a8`; tag `v1.2.0` cố định ở commit này.
- Release ID `403796965` đã công khai (`prerelease=true`); ba asset và link tải không đăng nhập đã xác minh.
- Evidence phát hành cuối: `checkpoints/evidence/v1.2.0/`.

Website giữ embed video YouTube gốc dài; kho/output được phân bổ cho nhóm/Page tick **Post hằng ngày**, upload trước để Facebook giữ lịch. Lỗi terminal Meta được phục hồi qua UI với MP4 đã sửa và giờ mới, giữ bài/ID cũ. Website retry sửa đúng URL cũ.

Chưa cài bản này vào runtime đang dùng hoặc đăng lại các bài Meta/CMS thật trong lượt phát hành. Session sau kiểm tra `build_identity.json` của app đang chạy trước, rồi đọc diagnosis đúng Video ID.

Checkpoint lịch sử `v1.1.9-autopublish5` vẫn ở `release/CODEX_CHECKPOINT_v1.1.9-autopublish5.md`. Hai lỗi `368/4854002` yêu cầu quản trị viên xác minh danh tính trên Facebook; không coi là lỗi MP4 hoặc đã được giải quyết bởi bản mới.
