# Highlight Video Studio

Ứng dụng Windows tạo highlight, nghiên cứu nội dung, đăng Reel đa kênh, xuất bản bài website và First Comment.

Bản mới: **1.2.0**. Xem [checkpoint v1.2.0](CHECKPOINT_V1_2_0_20261005.md) để tiếp tục sửa lỗi từ đúng source và bộ cài.

## Cài đặt

Tải bộ cài mới nhất trong GitHub Releases, chạy file và bấm **Cài đặt & khởi chạy**. Bản cài gồm Python portable cùng các engine cần thiết; người dùng không phải cài Python hoặc chạy lệnh thủ công.

Installer tạo shortcut có icon tại Desktop và Start Menu. Khi cài đè bản mới, cấu hình, token, lịch đăng, video đã tải và Chrome profile được giữ nguyên.

## Cấu hình AI

Trong **Cấu hình AI & Engine**, nhập endpoint OpenAI-compatible và API key, sau đó:

1. Bấm **Lấy danh sách Models**.
2. Chọn model.
3. Bấm **Test model đã chọn** để xác minh bằng một request chat thật.

Endpoint có thể nhập ở dạng root, `/v1`, `/models` hoặc `/chat/completions`; ứng dụng tự chuẩn hóa. Các gateway OpenAI-compatible như 9Router hoặc CLIProxyAPI được hỗ trợ khi chúng cung cấp `/models` và `/chat/completions`.

## Website và video

Bài viết website ưu tiên nhúng video YouTube gốc bằng iframe responsive trong nội dung CMS. Link YouTube không được in thành liên kết chữ trong bài và MP4 không được upload khi metadata có YouTube ID hợp lệ. Luồng upload MP4 chỉ được giữ làm fallback cho dữ liệu cũ không có nguồn YouTube.

Không commit API key, mật khẩu CMS, Facebook token hoặc SSH private key vào GitHub.
