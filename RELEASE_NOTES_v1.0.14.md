# Highlight Video Studio v1.0.14

- Sửa lỗi `'NoneType' object is not callable` tại bước transcript khi video không trả phụ đề qua `youtube-transcript-api` và máy chưa có `faster-whisper`.
- Thêm fallback tải phụ đề tự động JSON3 bằng yt-dlp portable, có hỗ trợ Chrome profile khi YouTube yêu cầu đăng nhập.
- Chuẩn hóa JSON3 về transcript có timestamp để LLM và renderer sử dụng trực tiếp, nhanh hơn nhiều so với nhận diện lại audio của video dài.
- Nếu video thực sự không có phụ đề và thiếu Whisper, hiển thị lỗi rõ nguyên nhân thay vì lỗi `NoneType`.
- Bao gồm bản vá lazy pipeline binding và installer file-lock của v1.0.13.
