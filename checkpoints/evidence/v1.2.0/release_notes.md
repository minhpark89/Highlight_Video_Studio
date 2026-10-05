# Highlight Desktop Test 1.2.0

Video hoàn chỉnh có sẵn trong kho/output được nhận tự động và phân bổ cho nhóm/Page đã tick **Post hằng ngày**. App upload trước để Facebook giữ lịch và tự đăng; Website tiếp tục nhúng video YouTube gốc dài theo cấu hình, First Comment dẫn tới bài trên Website của chúng ta.

- Thêm lựa chọn duyệt Draft hoặc tự động, ledger chống đăng trùng qua restart/đổi tên/nhập lại, cùng cleanup sau khi xác minh đăng thành công.
- Sửa MP4 rỗng do mốc cắt vượt thời lượng nguồn. Kiểm tra video stream và duration trước khi đưa file vào kho hoặc upload Meta.
- Kiểm tra Meta đúng upload Video ID; hỗ trợ chọn MP4 đã sửa và giờ mới để tạo lịch thay thế khi Meta xác nhận video cũ lỗi. Giữ lịch sử và IDs cũ.
- **Thử lại Website** sửa đúng bài tại URL đã có, giữ YouTube embed và phục hồi First Comment đúng URL.

Source đóng gói: `a199630d39d636e0c1b9173f12691cf2da1436a8`, tag cố định `v1.2.0`, nhánh `release/v1.2.0`.

Kiểm chứng: **567 passed, 3 skipped, 29 subtests passed**; browser offline daily/Draft/recovery qua và không có JavaScript pageerror. Payload được đối chiếu source sạch, không chứa credential hoặc dữ liệu runtime của máy build.

Tải `Highlight_Desktop_Test_Setup_v1.2.0.exe`; file `.sha256` dùng kiểm tra bộ cài. Checkpoint đính kèm ghi nguyên nhân lỗi, cách đăng lại qua UI, cách kiểm tra phiên bản app đang chạy và cách tiếp tục session fix từ đúng commit.

Đây là bản desktop test theo workflow hiện tại. Chưa cài lên runtime người dùng hoặc thử đăng lại các bài Meta/CMS thật trong lượt phát hành này. Lỗi Meta yêu cầu xác minh danh tính `368/4854002` vẫn cần quản trị viên xử lý trên Facebook.
