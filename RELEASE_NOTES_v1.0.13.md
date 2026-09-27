# Highlight Video Studio v1.0.13

- Sửa lỗi `name 'download_video_and_audio' is not defined` khi worker bắt đầu xử lý job.
- Nguyên nhân: pipeline đã chuyển sang lazy import nhưng `run_job_pipeline()` chưa bind sáu hàm import vào scope cục bộ.
- Worker giờ resolve đồng thời downloader, transcript, Whisper, LLM highlight, renderer và video-ID extractor trước bước 1.
- Thêm regression test chạy giả lập trọn pipeline từ download đến trạng thái completed, bảo đảm cả sáu hàm lazy đều được resolve.
- Thông báo Chrome fallback hiển thị đúng profile thuộc thư mục cài hiện tại, không còn ghi cứng ổ `D:`.
- Bao gồm installer auto-stop/file-lock fix của v1.0.12.
