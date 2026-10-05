# Checkpoint mới nhất — Highlight Desktop Test v1.2.0

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
