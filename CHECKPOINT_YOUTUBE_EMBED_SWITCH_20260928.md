# CHECKPOINT — Chuyển bài website sang YouTube embed (2026-09-28 22:15 GMT+7)

## Yêu cầu mới của boss (task đang dở)
Thay vì upload video MP4 gốc lên server/hosting của boss (nặng, tốn băng thông khi nhiều video),
hãy **chuyển link YouTube gốc thành dạng embed code rồi dán vào bài viết**.

Cách làm boss đề xuất:
1. Trên web CMS đã có hỗ trợ embed code.
2. Kiểm tra API của web xem có phần nhận embed code không.
3. Dùng chính link YouTube gốc của video → dạng `https://www.youtube.com/embed/<VIDEO_ID>` (hoặc iframe).
4. **KHÔNG** phải đưa file lên server của boss nữa.

## Phạm vi an toàn (giữ nguyên như các checkpoint trước)
- Worktree duy nhất: `F:\openclaw\.openclaw\workspace\worktrees\highlight-multi-pc`
- Branch: `feature/multi-pc-control-plane`
- KHÔNG sửa/restart/ghi vào production `D:\Highlight_Video_Studio` / port 5080.
- KHÔNG dùng token/key thật trong test, KHÔNG đăng Facebook thật.
- KHÔNG commit/build/release cho tới khi boss duyệt.

## Trạng thái git hiện tại (khi tạo checkpoint)
```
## feature/multi-pc-control-plane...origin/feature/multi-pc-control-plane
 M config/website_config.json
 M core/website_article_service.py
 M tests/test_website_ui_regression.py
 M web/app.py
 M web/index.html
 M web/templates/index.html
```
HEAD hiện tại: `6c933db use generic CMS media uploader by default`

Lịch sử gần nhất:
```
6c933db use generic CMS media uploader by default
3237d79 fix website upload fallback for CMS 403
12e630d create website articles when scheduling preview.7
6c49b59 restore website CMS settings UI for preview.6
faab0fd harden scheduled publishing recovery and preview.5
```
→ Nghĩa là: preview.6 (khôi phục UI Website) và preview.7 (tạo bài website ngay khi lên lịch)
đã xong và commit. Phần đang dở (uncommitted) là CMS uploader mặc định + test UI.

## Các file/khu vực quan trọng cho task mới

### 1. Nơi tạo bài website cho 1 clip (ĐIỂM SỬA CHÍNH)
`src/publisher/website_publisher.py`
- `publish_clip_to_website_cms(clip_filename, video_title=None) -> (article_url, hero_image_url)`
  - Dòng ~623. Luồng hiện tại:
    1. `get_clip_metadata(clip_filename)` → lấy meta (title, **youtube_url**, youtube_id, long_video_path)
    2. `upload_long_video_to_public_stream(meta, clip_filename)` → **UPLOAD MP4 LÊN HOSTING** (cần bỏ/thay thế)
    3. `extract_and_upload_article_assets()` → ảnh hook AI + frame minh họa
    4. `generate_deep_article_content(video_title, hero_img, body_imgs, video_stream_url)` → HTML bài viết
    5. `svc.publish_article(title, slug, body_html, image_url=hero_img)`
- `upload_long_video_to_public_stream()` dòng ~289 — chính là chỗ gọi `svc.upload_video()`.
- `generate_deep_article_content()` dòng ~396 — chỗ nhúng khối `<video ...><source src="{video_stream_url}">`.
  - Có guard: `if not video_stream_url or not str(video_stream_url).startswith("https://")` → raise. Cần đổi để nhận YouTube embed URL.
  - Khối video nằm ở CUỐI bài, trong `<div class="full-video-section">`.

### 2. Metadata YouTube đã có sẵn (KHÔNG cần crawl lại)
`get_clip_metadata()` trong cùng file, dòng ~125:
- Đọc `jobs.json` (HVS_DIR) → `youtube_url` theo `clips[].filename == clip_filename`
- Suy ra `youtube_id` từ `?v=` hoặc `youtu.be/`
- `long_video_path` = `HVS_DIR/downloads/{job_id}.mp4`
→ Chỉ cần build embed URL: `https://www.youtube.com/embed/{youtube_id}`
(Chú ý: `jobs.json`/`crawled_videos.json` nằm ở HVS_DIR — với bản cài là thư mục app; test dùng fixture.)

### 3. Nơi gọi khi lên lịch
`web/app.py`
- `prepare_website_article_for_schedule(...)` dòng ~95 → gọi `publish_clip_to_website_cms` (dòng ~123)
- Route retry: `/api/posts/<post_id>/retry-website` (POST) dòng ~2124
- Route publish draft: `/api/website/publish_draft` (POST) dòng ~2611 — có body_html riêng nhúng `<video controls>` (dòng ~2673)

### 4. Backend CMS (core service)
`core/website_article_service.py`
- `WebsiteArticleService.publish_article(title, slug, body_html, image_path=None, image_url="", dry_run=False)` dòng ~395
- Payload gửi lên CMS: `POST {api_base_url}/posts` với các field:
  `title, slug, description (=body_html), image, seo_*, og_*, twitter_*, is_active, is_home, is_top, category_ids, tag_ids`
- → **Cần verify**: field `description` (HTML) của CMS có render `<iframe>` (YouTube embed) không,
  hoặc CMS có field/route riêng cho "embed code" / "video url" / "embed_html" hay không.
  (Boss nói trên web có hỗ trợ embed code → phải kiểm tra API thực tế của CMS.)
- `upload_video()` dòng ~321, `verify_public_media()` ~349 — chỉ dùng cho method scp/cms upload.

### 5. Config
`config/website_config.json` (đang modified, cần CHÚ Ý ĐỪNG commit máy-specific):
```json
{
  "base_url": "",
  "username": "",
  "password": "",
  "video_upload": {
    "method": "scp",
    "host": "157.173.116.71",
    "port": 22,
    "username": "root",
    "private_key_path": "%USERPROFILE%\\.ssh\\bob2_auto",
    "remote_dir": "/var/www/portfolio/videos",
    "public_base_url": "https://studio.shopkitai.com/videos"
  }
}
```

### 6. Tests liên quan
- `tests/test_scheduling_publish_flow.py` — lifecycle khi lên lịch, CMS failure, retry website
- `tests/test_website_ui_regression.py` — UI Website pane, CMS method mặc định
- `tests/test_page_token_sync.py`, `tests/test_release_guards.py`

## Việc cần làm tiếp (thứ tự đề xuất)
1. **Kiểm tra API CMS thật**: gọi `/api/website-config/test` hoặc xem route backend `/posts`
   để xác nhận nhận `description` HTML có iframe hay không, hoặc có field embed riêng.
   → Nếu có: chỉ cần đổi `body_html` sang iframe YouTube.
   → Nếu không: cần thêm field/route, hoặc fallback sang HTML5 `<video>` khi không có YouTube id.
2. Sửa `generate_deep_article_content()` để nhận `video_embed_html` (iframe) hoặc `video_stream_url`,
   ưu tiên YouTube embed khi có `youtube_id`.
3. Sửa `publish_clip_to_website_cms()`:
   - Nếu có `youtube_id` → BỎ bước `upload_long_video_to_public_stream`, dùng embed.
   - Chỉ upload MP4 khi không có link YouTube (fallback), hoặc theo config switch.
4. (Tùy chọn) thêm config `website_config.json → video_embed.mode = "youtube" | "upload"`.
5. Cập nhật/thêm test: bài có youtube_id → body_html chứa iframe embed, KHÔNG gọi upload_video.
6. Chạy targeted test rồi full suite. Không commit/build cho tới khi boss duyệt.

## Ghi chú phiên làm việc
- Session Telegram đang chạy ở ~37k/200k token → chưa tràn, nhưng sẽ tạo checkpoint này
  để boss mở session mới đọc và tiếp tục an toàn.
- Các checkpoint cũ trong cùng worktree:
  - `CHECKPOINT_ENDPOINT_TOKEN_FIX_20260928.md`
  - `CHECKPOINT_PREVIEW5_WEBSITE_UI_20260928.md`

<!-- project: path:F:\openclaw\.openclaw\workspace -->
