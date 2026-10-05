Các bài quá hạn hoặc upload dở được app tự khôi phục trên Meta ID đã lưu. App tự thử lại lỗi tạm thời theo thời gian chờ tăng dần và tiếp tục First Comment khi Meta xác nhận bài đã đăng.

- Hoàn tất upload cũ, xử lý lịch Meta quá hạn và chuyển lịch hết cửa sổ về hàng đợi app tại giờ đã chọn.
- Lưu trạng thái trước khi gửi Finish; sau timeout hoặc khởi động lại, đối soát ID cũ trước khi thử tiếp để tránh đăng trùng.
- Khôi phục cả bài từng bị từ chối trong lần Finish thủ công ở bản cũ.
- Tự xử lý nội dung social cũ chưa đúng tiếng Anh; tiếp tục retry First Comment sau 8 lần thất bại.
- Hiển thị rõ yêu cầu xác minh danh tính Facebook. App giữ bài và ID để tự thử lại sau khi tài khoản được cấp quyền đăng.

Kiểm chứng: **451 passed, 3 skipped, 29 subtests passed**. Payload sạch, 8005 mục; mã nguồn và bản cài đặt khớp commit `acb74e23ca8e204bfbb989eb6763d9b161abc864`.

Đã cập nhật và kiểm tra app đang chạy: 398/400 bài đã đăng, 398 First Comment thành công. 11 bài vừa khôi phục và 11 comment đã được đọc lại trực tiếp qua Meta API. Hai bài còn chờ Facebook yêu cầu xác minh danh tính, mã `368 / 4854002`; app tiếp tục thử lại theo backoff. Không thể vượt qua yêu cầu xác minh của Facebook bằng mã app.

Cài vào thư mục app hiện tại để giữ dữ liệu. Installer bảo toàn cấu hình, token, lịch sử bài, dữ liệu hàng đợi và video; checkpoint đính kèm ghi kết quả cùng bước tiếp tục.

SHA-256 installer:
`0cba2a07d415db8475fe016ec2ddd3fa477b4ef5c16596248e701cc68d472419`
