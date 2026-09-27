# Highlight Video Studio v1.0.17

## Image AI endpoint hotfix

- Tách riêng `Endpoint tạo ảnh` và `Endpoint lấy model` vì mỗi provider có thể dùng đường dẫn khác nhau.
- Endpoint `/models` là tùy chọn; lỗi HTTP 404 khi lấy model không còn chặn việc nhập model thủ công hoặc kiểm tra tạo ảnh.
- Cho phép nhập tên model ảnh thủ công, đồng thời vẫn hỗ trợ gợi ý model từ endpoint riêng.
- Test tạo ảnh dùng đúng URL đầy đủ do người dùng nhập và tự chọn payload tương thích với `/images/generations` hoặc `/chat/completions`.
- Pipeline tạo ảnh thực tế dùng cùng endpoint đã test trong Settings.
- Giữ tương thích cấu hình v1.0.16: nếu chỉ có `api_base`, app tự suy ra endpoint OpenAI-compatible cũ.
- Tiếp tục giữ chế độ miễn phí `__video_frame__` để trích frame video thay cho AI ảnh.

## Verification

- Python syntax check passed.
- Release guard suite: 16/16 tests passed.
- Hotfix deployed to the primary app at `D:\Highlight_Video_Studio` and verified HTTP 200 on port 5080.
- Live Settings UI verified to contain separate generation/model endpoint controls.
