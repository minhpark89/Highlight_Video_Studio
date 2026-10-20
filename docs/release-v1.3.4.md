# Highlight Desktop Test v1.3.4

Bản cập nhật sửa lỗi màn hình đen khi mở Draft theo nhóm, mở Token từ thông báo và các liên kết nhanh trên Dashboard.

- Đối soát Meta chạy ở luồng riêng, tiếp tục đọc trạng thái khi một lượt upload đang bận. Mỗi lượt kiểm tra có giới hạn, ưu tiên lịch quá giờ và bài thất bại chưa rõ kết quả; vẫn dành lượt cho các bài cũ.
- Đối soát không chờ tác vụ dọn video trên ổ đĩa; việc dọn file vẫn do worker lưu trữ độc lập thực hiện. Ảnh YouTube không còn tồn tại được thay bằng ảnh dự phòng có cache.
- Các Token/Page khác nhau có thể được đọc song song tối đa bốn lượt. Quyền bị chặn được giãn thời gian kiểm tra. Bảng bài đăng hiển thị riêng hàng đợi Meta, lịch quá giờ, lần kiểm tra và nút yêu cầu kiểm tra ngay.
- Bài thất bại đã có Meta ID được tự đối soát lại trên video hiện có. Liên kết Page/videos và Watch hợp lệ cũng được chấp nhận khi Meta xác nhận đúng video đã xuất bản.
- Bài chưa lưu Meta ID có công cụ tìm video trùng nội dung và gắn video đã được xác minh thuộc đúng Page. Nếu đã kiểm tra Page và xác nhận chưa có bài, có thể chuyển về Draft rồi chọn lịch và duyệt lại. App giữ lịch sử đối soát và ngăn gắn một video vào hai bài.
- Việc hoàn tất upload hoặc xử lý lịch quá giờ vẫn giữ nguyên Meta ID, khóa chống gửi trùng và bước kiểm tra quyền. Meta yêu cầu xác minh danh tính hoặc chặn API thì cần xử lý quyền trên Facebook/Meta; app hiển thị hướng xử lý tương ứng.
- Giữ các cải tiến đã cài riêng trên PC ngày 13/10: phục hồi launcher, giới hạn bảo trì comment, chọn model LLM khả dụng, giảm Whisper không cần thiết, sử dụng khung hình từ clip còn trong kho và điều khiển thử lại Website.

Installer nâng cấp giữ nguyên dữ liệu, Token, Page, bài đăng, lịch và thiết lập của người dùng, đồng thời tạo bản sao lưu trước khi thay mã. Payload phát hành không chứa Token, credential hoặc dữ liệu hàng đợi của PC.
