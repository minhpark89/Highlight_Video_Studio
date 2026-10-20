# Highlight Desktop Test v1.3.5

Bản cập nhật đầy đủ các sửa lỗi Draft/Token và đối soát Meta của v1.3.4, kèm sửa vòng lặp thất bại ở bài cũ có nội dung pha tiếng Anh và tiếng Việt.

- Kiểm tra ngôn ngữ trên đúng mô tả Reel sau khi ghép tiêu đề và nội dung. Nếu từng trường vượt qua riêng lẻ nhưng mô tả ghép bị từ chối, app chuyển sang nội dung tiếng Anh dự phòng, cập nhật gói nội dung liên quan và giữ nguyên URL Website. Ca lỗi thực tế đã được bổ sung vào kiểm thử hồi quy.
- Mở Draft theo nhóm, Token từ thông báo và các liên kết Dashboard không còn làm mất giao diện.
- Đối soát Meta chạy độc lập với upload và dọn ổ đĩa; ưu tiên lịch quá giờ và bài thất bại chưa rõ kết quả, đồng thời dành lượt cho bài cũ. Tối đa bốn Token/Page khác nhau được đọc song song.
- Bài thất bại có Meta ID được kiểm tra lại trên video hiện có. Bài thiếu ID có công cụ tìm và gắn video đúng Page; chỉ chuyển về Draft sau khi người dùng xác nhận đã kiểm tra Page và chưa có bài.
- Hàng đợi hiển thị trạng thái đối soát, lần kiểm tra và nút Ưu tiên kiểm tra Meta. Yêu cầu hủy cũ được giữ nguyên; app không tự đăng lại bài đang yêu cầu hủy.
- Giữ các cải tiến trên PC ngày 13/10: phục hồi launcher, giới hạn bảo trì comment, chọn model LLM khả dụng, giảm Whisper không cần thiết, khung hình dự phòng từ clip và điều khiển thử lại Website.

Khi Meta yêu cầu xác minh danh tính hoặc chặn quyền API/Page, cần hoàn tất thao tác đó trên Facebook/Meta rồi đồng bộ Token/Page trong app. Việc tăng số luồng không vượt qua được giới hạn này.

Installer tạo bản sao lưu và giữ dữ liệu, Token, Page, bài đăng, lịch cùng thiết lập. Payload phát hành không chứa credential hoặc dữ liệu hàng đợi của máy build.
