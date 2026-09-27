# Highlight Video Studio v1.0.11

- Sửa dứt điểm `[WinError 32]` khi nhiều worker đồng thời cập nhật `jobs.json`.
- Loại định nghĩa `save_jobs()` trùng từng vô hiệu hóa cơ chế khóa ở bản trước.
- Chu kỳ đọc–sửa–ghi job giờ dùng khóa re-entrant; mỗi lần lưu dùng file tạm duy nhất, flush và atomic replace có retry riêng cho Windows.
- Cho phép chọn model riêng cho phân tích Highlight, viết bài website, First Comment và tạo ảnh Hook.
- Nút kiểm tra AI xác minh chat thật cho toàn bộ model đang được chọn.
- Có lựa chọn ảnh ổn định từ frame video khi provider không cung cấp model tạo ảnh.
- Tăng tính tương thích gateway bằng Bearer, `x-api-key` và `api-key` cho mọi tác vụ bài viết.
- Nội dung do LLM sinh được HTML-escape trước khi đưa vào bài nhằm tránh markup không an toàn.
- Đã xác minh CMS `bestnews.cfx.bz`: đăng nhập, Posts API, presigned image upload và public image đều hoạt động.
