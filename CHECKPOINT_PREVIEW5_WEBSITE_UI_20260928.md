# Checkpoint — preview.5 và lỗi thiếu cấu hình Website (2026-09-28)

## Phạm vi an toàn
- Worktree duy nhất: `F:\openclaw\.openclaw\workspace\worktrees\highlight-multi-pc`
- Branch: `feature/multi-pc-control-plane`
- Không sửa, restart hoặc ghi đè production `D:\Highlight_Video_Studio` / port 5080.
- Không dùng token/key thật trong test và không tự động đăng Facebook thật.

## Bản phát hành gần nhất
- Release: `v1.0.19-desktop-test.5`
- Installer: `Highlight_Desktop_Test_Setup_v1.0.19-preview.5.exe`
- Commit phát hành: `faab0fd58ccccf53bad2fdd4bf7292ed33bd1d81`
- SHA256: `3abd37cc6ce3ea0767a5266d9c6e9ceb22199a746d360e9d9942e0dd27f372a1`

## Các phần đã hoàn thành trước preview.5
1. Endpoint tạo ảnh tách riêng `/v1/images/generations`; có fallback frame không-AI.
2. Tối ưu quản lý 31 token / khoảng 100 page bằng representative sync, lightweight `/me`, snapshot page binding và local rebind.
3. Lifecycle đăng bài tách Facebook Reel, First Comment retry queue, Website CMS, Facebook permalink và preview/download MP4.
4. Website CMS upload video dài gốc và render HTML5 player.
5. `web/posts_store.py`: ghi `posts.json` atomic, backup/recovery, không được đọc lỗi rồi ghi đè queue thành rỗng.
6. Scheduled publisher: khôi phục stale `publishing`, xử lý bài quá hạn, heartbeat API, trạng thái `failed/retryable`, nút chạy bài đến hạn và UI auto-refresh/cảnh báo overdue.
7. Installer cài đè bản test cũ nhưng bảo toàn dữ liệu: `config.json`, `config/website_config.json`, `posts.json`, `jobs.json`, `pages.json`, `page_groups.json`, `tokens_vault.json`, và các thư mục `downloads/`, `output/`, `chrome_profile/`, `data/`.
8. Regression suite trước release: 81 tests pass.

## Lỗi thực tế boss phát hiện trên PC test
- Boss đã cài và test `preview.5`.
- Sidebar không còn mục **Cấu hình Website/CMS**.
- Bảng quản lý bài đăng hiển thị `Website: tạo thất bại`; post có badge lỗi có thể thử lại.
- Backend API và JavaScript Website vẫn tồn tại (`/api/website-config`, `/api/website-config/test`, `/api/website-config/test-video`, `loadWebsiteConfig`, `saveWebsiteConfig`), nhưng các HTML field và pane tương ứng bị mất khỏi template hiện tại.
- `config/website_config.json` trong installer chỉ là cấu hình rỗng mặc định. Installer có chính sách giữ file cũ nếu tồn tại, nhưng máy chưa cấu hình hoặc cần sửa cấu hình không có UI để thao tác.

## Nguyên nhân đã định vị
- Current `web/index.html` và `web/templates/index.html` có JS truy cập các element như `cfg_web_base`, `cfg_web_user`, `cfg_web_pass`, v.v. nhưng không còn `pane-website` và nút sidebar.
- Lịch sử Git cho thấy commit `0167ee5126178cb71bf7dacd1e46adb8a9216d86` còn đầy đủ:
  - nút `data-pane="pane-website"`;
  - `<section id="pane-website">`;
  - các field CMS/video uploader;
  - lazy loader `loadWebsiteConfig()` khi mở tab.
- Đây là regression giao diện/template, không phải API Website bị xóa hoàn toàn.

## Việc tiếp theo
1. Khôi phục có kiểm soát nút sidebar và pane Website từ phiên bản lịch sử vào cả hai template hiện hành, không rollback các sửa preview.5.
2. Thêm regression test bắt buộc kiểm tra pane và toàn bộ field Website tồn tại ở cả `web/index.html` và `web/templates/index.html`.
3. Kiểm tra API lưu/đọc config không làm lộ password và installer tiếp tục preserve `config/website_config.json`.
4. Chạy test mục tiêu, sau đó full release suite.
5. Nếu pass, bump `preview.6`, đóng gói installer test mới và phát hành để boss cài đè; không chạm production.

<!-- project: path:F:\openclaw\.openclaw\workspace -->
