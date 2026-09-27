# Highlight Video Studio v1.0.12

- Sửa lỗi installer không thể ghi đè `runtime/libcrypto-3.dll` khi server portable cũ còn chạy.
- Installer tự tìm và đóng mọi tiến trình chạy từ thư mục đích trước khi nâng cấp.
- Ưu tiên đóng mềm, sau đó dừng cưỡng chế nếu tiến trình không thoát trong thời gian chờ.
- Mỗi file được giải nén vào file tạm trước, rồi copy đè với retry; tránh để lại file ứng dụng bị ghi dở nếu Windows còn giữ file.
- Tiếp tục giữ nguyên cấu hình, token, jobs, Chrome profile, downloads và output khi nâng cấp.
- Bao gồm toàn bộ sửa lỗi job concurrency, CMS và lựa chọn model theo tác vụ của v1.0.11.
