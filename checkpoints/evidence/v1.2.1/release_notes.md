# Highlight Desktop Test 1.2.1

Câu tiếng Anh ngắn từng bị nhận nhầm ngôn ngữ, khiến Website chưa ready và First Comment bị chặn. Bản này xác minh toàn bài Website tại URL đang có, giữ YouTube embed gốc và chuẩn bị First Comment chứa đúng URL một lần.

- Thêm màn **Chuẩn bị & Draft theo nhóm Page**: thấy Page, Token, giờ đăng; lọc nhóm/Page/trạng thái, mở bài, duyệt một hoặc nhiều Draft và retry Website.
- Phân bổ Page/Token Group trước khi chuẩn bị Content. Nhóm mới mặc định **Duyệt tay → Draft**; nhóm cũ giữ lựa chọn đã lưu. Có thể chọn App hoặc Meta giữ lịch.
- Phân trang quản lý 50 dòng và review nhóm 30 dòng; Token audit tải khi cần. Worker không viết lại queue 800 bài khi không có thay đổi.

Kiểm chứng: **581 passed, 3 skipped, 29 subtests passed**; browser offline không có JavaScript error. Ba Website thực tế trả HTTP 200 và có English/YouTube embed hợp lệ. Bộ cài khớp 17 file runtime tại source sạch, không chứa credential hoặc state của máy build.

Tag cố định `v1.2.1` trỏ tới source đóng gói `edfdd753800c0171e5758b25b9da8a3b96766df3`. Nhánh [release/v1.2.1](https://github.com/minhpark89/Highlight_Video_Studio/tree/release/v1.2.1) lưu checkpoint, tools và evidence cập nhật.

Tải `Highlight_Desktop_Test_Setup_v1.2.1.exe`, kiểm tra bằng `.sha256` đi kèm. SHA-256: `d9b4378cd5ee8e0fe695d13a4a5e72fd16c847999769db40cb0d5f39a9c03fce` (705,059,328 bytes).

`CODEX_CHECKPOINT_v1.2.1.md` đính kèm ghi cách kiểm tra app đang chạy, sao lưu dữ liệu, tiếp tục session fix và retry đúng Website/First Comment. [Checkpoint cập nhật](https://github.com/minhpark89/Highlight_Video_Studio/blob/release/v1.2.1/CHECKPOINT_V1_2_1_GROUP_REVIEW_20261006.md) lưu kết quả phát hành cuối cùng.

Đây là bản desktop test/prerelease. Lượt phát hành chưa cài vào runtime người dùng hoặc tạo/xóa Reel/comment Meta thật. Sau khi cài, dùng **Thử lại Website** ở bài bị chặn; giữ các Meta IDs và receipt đã có. Lỗi Meta yêu cầu xác minh danh tính `368/4854002` vẫn cần quản trị viên xử lý trên Facebook.
