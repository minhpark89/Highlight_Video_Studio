# Highlight Desktop Test v1.1.9-autopublish4

Cho phép nhập trực tiếp số luồng đăng và số luồng Content/LLM từ **1–32**. Nhấn Enter hoặc rời ô để lưu; giá trị được giữ sau khi mở lại app. Khi giảm số luồng, tác vụ đang chạy tiếp tục đến khi hoàn tất.

Thêm nút **Đồng bộ quyền và thử đăng lại** trong **Kiểm tra Meta**. App lấy lại Page token từ Token đã chọn, xác minh đúng Page và quyền tạo nội dung, đọc trạng thái video rồi thử hoàn tất đăng trên ID cũ. Có thể chọn một Token quản lý khác đã được xác minh cho cùng Page.

Scheduler cũng tự làm mới Page mapping trước khi thử lại lỗi xác minh danh tính. Mọi lần thử giữ nguyên video và Token ID gốc; phản hồi đã nhận hoặc chưa rõ kết quả được đối soát trước khi gửi tiếp.

**Kiểm chứng:** 482 passed, 3 skipped, 29 subtests passed. Đã kiểm tra thao tác nhập 7 luồng đăng và 6 luồng Content/LLM trên app thật, lưu qua reload, từ chối số 33 và 2.5. Installer có 8.006 mục, không kèm token hoặc dữ liệu người dùng. Cài đè đã giữ nguyên 26 file dữ liệu; scheduler hoạt động và hàng đợi render đã tiếp tục.

**Kết quả hai bài còn lỗi:** Token gốc vẫn ACTIVE và có CREATE_CONTENT. Sau khi lấy Page token mới và thử thêm một Token quản lý khác, Meta vẫn từ chối cả hai video bằng mã `368 / 4854002`. Đây là yêu cầu xác minh danh tính từ Facebook; làm mới token chưa đủ giải quyết. Quản trị viên cần hoàn tất xác minh trên Facebook. App giữ nguyên hai ID và tiếp tục retry có backoff.

| Bài | Meta ID giữ nguyên |
| --- | --- |
| `post_1791121129_7e1a6d` | `1373334701223226` |
| `post_1791121324_dae163` | `1722433486142952` |

Cài vào thư mục app hiện tại để giữ cấu hình, token, lịch sử và hàng đợi. Checkpoint đính kèm ghi commit, kết quả kiểm tra và các bước tiếp tục.

Source commit: `181b05236687d92cfb5f1eaf46f90f1c28807bc6`.

Installer: `704499712` bytes. SHA-256:

`62396dabd0774359cb923e34a42358144e5edf9a109c13141591a15570251285`

Release mới dùng tag `v1.1.9-autopublish4`; bản `autopublish3` được giữ nguyên.
