# Highlight Desktop Test v1.1.9-autopublish5

Hai bài trên Page Lucas Bryant vẫn đọc được qua API, token ACTIVE và có quyền tạo nội dung, nhưng Meta từ chối lệnh xuất bản bằng **HTTP 400, code 368, subcode 4854002**. Bản này lưu riêng phản hồi đăng để một lần đọc trạng thái HTTP 200 không che mất lỗi xuất bản.

- Bảng bài đăng hiển thị đúng Token đang dùng để phục hồi; Token gốc được ghi riêng. Sửa trường hợp đã chọn Autopost25 nhưng bảng vẫn chỉ hiện Autopost23.
- Tách số lần đọc trạng thái khỏi số lần thử đăng.
- Trong **Kiểm tra Meta**, xem trạng thái credential, mapping Page, quyền tạo nội dung và phản hồi đăng gần nhất: thời gian, endpoint, HTTP, code/subcode và trace ID.
- Nút **Sao chép báo cáo lỗi** sao chép bằng chứng chẩn đoán, không chứa giá trị access token.
- Tiếp tục dùng **Đồng bộ quyền và thử đăng lại**: app làm mới Page token, xác minh đúng Page, đọc trạng thái video và thử đăng lại trên Meta ID hiện có. Scheduler tự retry có backoff; giữ nguyên ID để tránh đăng trùng.
- Số luồng đăng và Content/LLM nhập trực tiếp từ **1–32**, lưu bằng Enter hoặc rời ô.

**Lỗi hiện tại cần xử lý trên Facebook:** Meta trả nguyên văn “Bạn cần xác nhận danh tính của mình rồi mới có thể đăng dưới tên Trang này. Hãy mở ứng dụng Facebook trên điện thoại và làm theo hướng dẫn.” Mã lỗi là yêu cầu xác minh quyền xuất bản của Page/tài khoản quản lý, dù token vẫn hợp lệ. Quản trị viên cần kiểm tra xác minh trong Facebook/Meta Business Suite của đúng Page. Sau khi Meta cho phép, để app tự retry hoặc bấm nút phục hồi. App không thể vượt qua checkpoint này.

**Kiểm chứng:** 482 passed, 3 skipped, 29 subtests passed; installer sạch, 8.006 mục, 24 hash mã nguồn khớp; cài đè giữ nguyên 26 file dữ liệu và 400 bài. Đã thử hai lệnh đăng qua app mới: đều lưu được HTTP 400 / 368 / 4854002 và trace ID. Đã kiểm tra hiển thị token phục hồi, copy báo cáo thật qua clipboard và ô số luồng qua reload. Cấu hình trả về 8 luồng đăng, 4 luồng Content/LLM.

Audit ngày 05/10/2026 lúc 11:42 Asia/Saigon: **398/400 bài published, 398 First Comments posted**. Hai Meta ID giữ nguyên: `1373334701223226` và `1722433486142952`. Đã đọc lại 11 bài phục hồi trước và 11 comment qua Meta API. Scheduler hoạt động, render queue đã resume.

Source commit đóng gói: `b40e27d3f1b94c8447ff29438db1500fa2a1d9e8`.

Installer: `704501760` bytes. SHA-256: `40ffe07f9f08cda10b2b8763b97eb9802319c4b1ebed07ae7041e107a60c6ed8`.

Cài vào thư mục app hiện tại để giữ cấu hình, token và lịch sử. Checkpoint đính kèm ghi bằng chứng, trạng thái hai bài và bước kiểm tra tiếp theo. Tag mới `v1.1.9-autopublish5`; giữ nguyên bản `autopublish4`.
