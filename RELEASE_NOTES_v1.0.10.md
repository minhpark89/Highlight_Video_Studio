# Highlight Video Studio v1.0.10

- Bổ sung Research vào luồng làm việc.
- Thêm lấy danh sách model và kiểm tra chat thật cho mọi endpoint OpenAI-compatible.
- Sửa lỗi model xuất hiện trong danh sách nhưng không có credential hoạt động.
- Đóng gói CMS publisher trong ứng dụng; không còn phụ thuộc ổ `D:` của máy build.
- Upload video qua SCP cấu hình được; không dùng SSH key hard-code.
- Chỉ công bố URL bài/video sau khi kiểm tra public thành công.
- Video HTML5 dùng `playsinline`, HTTPS và kiểm tra Range để phát/tua trên mobile/web.
- First Comment có hàng đợi bền vững và retry cho Reel được Meta lên lịch.
- Installer Windows một file, có icon, Python portable, shortcut Desktop/Start Menu và giữ dữ liệu khi nâng cấp.
- Loại API key, mật khẩu CMS và token thử nghiệm khỏi trạng thái mã nguồn hiện tại.
