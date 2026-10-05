# MP4 rỗng, đối soát Meta và sửa Website tại URL cũ

Ngày: 2026-10-05 (Asia/Saigon).

## Chẩn đoán thực tế

- Runtime đang mở: `E:/OPENCLAW/BOB/Highlight destop test`, bản `1.1.9-meta-cancel1`.
- Post `post_1791183244_b98215`, upload Video ID `1456548559709071`.
- MP4 clip 2: 262 bytes, không có stream; nguồn thật dài 129.613787s, mốc cắt cũ 210–268s nằm ngoài nguồn.
- Local GET `/api/posts/post_1791183244_b98215/meta-diagnosis` đọc được HTTP 200, `video_status=error`, upload complete/262 bytes, processing complete, publishing not_started, copyright false.
- Code 12 trong observation cũ là hậu quả đối soát thêm Finish `post_id` sau upload Video ID. Video status vẫn hợp lệ trên Video object; không thay bằng các Graph field chưa được xác minh.
- Ba bài chưa đăng bị chặn do package Website non-English tại URL đã tồn tại; nút Website cũ có thể tái sử dụng URL mà không sửa CMS, và UI giấu nút retry khi URL đã có.

## Sửa

- `src/media_validation.py`: kiểm tra container/stream, kích thước khung, thời lượng hữu hạn và file ổn định bằng ffprobe; thiếu ffprobe hoặc lỗi kiểm tra đều chặn upload.
- `src/pipeline.py`: mốc LLM nằm ngoài duration thật được loại và bù bằng đoạn hợp lệ; render kiểm tra nguồn và đầu ra thật trước khi rename MP4 cuối. FFmpeg exit 0 với đầu ra rỗng vẫn bị từ chối.
- Poster chặn invalid_media trước mọi Graph POST. Handoff/worker lưu lỗi local, không lặp upload mù; nút kiểm tra MP4 chỉ cho chạy lại sau khi file hợp lệ và chưa có Meta ID.
- Reconciliation đọc upload Video ID trước, giữ phase evidence và không thay observation bằng lỗi status của Finish Post ID.
- `repair_existing_website_article`: authenticated resolve đúng CMS ID/slug/version; dịch nội dung English, giữ media URLs, PUT đúng bài cũ; xác minh English và video embed. Package/comment chỉ trở lại ready khi Website verified.
- Website retry có URL cũ đi qua queue repair; UI vẫn hiện nút. First Comment giữ đúng một URL; bài đã frozen/đã đăng chỉ nhận cập nhật verification, không phát comment lần hai.
- `web/video_recovery.py` và API/UI: operator chọn MP4 đã sửa + giờ mới; fresh read phải xác nhận exact Video ID lỗi, upload complete, publishing chưa bắt đầu/thất bại và không copyright match. Tạo successor idempotent; bài cũ superseded giữ toàn bộ Meta IDs. Không tạo lịch thay thế cho trạng thái unknown/processing/scheduled/published.
- Giữ nguyên Website YouTube gốc dài, Meta upload trước để Facebook giữ lịch, daily group/Page opt-in của daily-stock2.

## Xác minh và artifact

- Full pytest: `567 passed, 3 skipped, 29 subtests passed`.
- Các test Meta transport dùng MP4 fixture thật; có regression MP4 rỗng 262 bytes, FFmpeg exit 0/empty, mốc quá EOF, giữ observation đúng ID, replacement idempotency/unknown state fences, CMS same-URL repair, immutable published comment.
- Browser offline: `support/video-recovery/evidence/ui_verify.json`, `recovery_dialog.png`; daily/Draft QA vẫn qua, không pageerror.
- Clip preview được render từ nguồn thực: `E:/OPENCLAW/BOB/support/video-recovery/job_1790748353_7c7164_clip_2_repaired.mp4`, mốc 37.31–92.31s, duration 55.033008s, 1080×1920, 36459456 bytes. Đây là đoạn chọn lại vì mốc cũ ngoài video; operator xem trước rồi copy vào output nếu dùng để tạo lịch thay thế. File runtime cũ và jobs.json chưa bị sửa.
- Installer: `E:/OPENCLAW/BOB/source-worktree/release/Highlight_Desktop_Test_Setup_v1.1.9-daily-stock3.exe`.
- Size: 681873408 bytes. SHA-256: `e36ca57b64d8073eb8a76c9aaaa57ccae84db2889cf2fc1a808e86dfcff1775a`.
- Payload đối chiếu 14 source files; credential seeds trống, không có runtime state. Report `support/video-recovery/evidence/installer_verify.json`; script `support/video-recovery/verify_payload.ps1`.
- Chưa cài lên runtime đang dùng; chưa POST/DELETE Meta thật hoặc PUT CMS thật trong lượt này. Các thao tác external trong regression đều là fixtures.
