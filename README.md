# Highlight Video Studio

Ứng dụng Windows tạo highlight, nghiên cứu nội dung, đăng Reel đa kênh, xuất bản bài website và First Comment.

## Cài đặt

Tải `Highlight_Studio_Setup_v1.0.10.exe` trong GitHub Releases, chạy file và bấm **Cài đặt & khởi chạy**. Bản cài gồm Python portable cùng các engine cần thiết; người dùng không phải cài Python hoặc chạy lệnh thủ công.

Installer tạo shortcut có icon tại Desktop và Start Menu. Khi cài đè bản mới, cấu hình, token, lịch đăng, video đã tải và Chrome profile được giữ nguyên.

## Cấu hình AI

Trong **Cấu hình AI & Engine**, nhập endpoint OpenAI-compatible và API key, sau đó:

1. Bấm **Lấy danh sách Models**.
2. Chọn model.
3. Bấm **Test model đã chọn** để xác minh bằng một request chat thật.

Endpoint có thể nhập ở dạng root, `/v1`, `/models` hoặc `/chat/completions`; ứng dụng tự chuẩn hóa. Các gateway OpenAI-compatible như 9Router hoặc CLIProxyAPI được hỗ trợ khi chúng cung cấp `/models` và `/chat/completions`.

## Website và video

Kết nối CMS và máy chủ video được kiểm tra riêng. Video chỉ được gắn vào bài sau khi upload thành công, truy cập bằng HTTPS và vượt qua kiểm tra HTTP Range (`206 Partial Content`) để phát/tua trên điện thoại và web.

Không commit API key, mật khẩu CMS, Facebook token hoặc SSH private key vào GitHub.
