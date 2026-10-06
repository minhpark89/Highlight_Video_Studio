# Checkpoint v1.2.3 — Lên lịch hôm nay theo nhóm Page

Ngày 2026-10-06, Asia/Saigon. Repo: https://github.com/minhpark89/Highlight_Video_Studio.
Nhánh `release/v1.2.3`; các tag v1.2.1 và v1.2.2 giữ nguyên. Bản này bao gồm sửa v1.2.2 chưa phát hành.

## Yêu cầu và nguyên nhân

Người dùng muốn đưa bài đang chuẩn bị của nhóm NEW vào hôm nay 06/10 thay vì 07/10, lấy video từ kho vào nhóm Page, thao tác mượt và có bản tải GitHub/checkpoint để sửa tiếp.
Daily plan `group:grp_1791020096_3` dùng 04:00 và 10:50, Meta mode, automatic, 15 phút/Token, 100 Pages. Daily bỏ khung quá gần hiện tại (20 phút cho Meta) và duyệt tiếp ngày mai. Snapshot 10:49 có 296 preparing trong nhóm: 97 lịch 06/10, 199 lịch 07/10; kho 531 video. Đây là hành vi Daily theo khung cố định, không phải lỗi UTC đổi ngày.

## Thay đổi

- Checkbox chọn được cả preparing và Draft. Duyệt chỉ nhận Draft đã sẵn sàng; lịch hôm nay có nút riêng cho bài chọn, cả nhóm, lấy từ kho.
- `POST /api/posts/schedule-today`: mặc định xem trước. Chọn ngày trên máy chạy app, giờ HH:MM, khoảng cách Token, App/Meta, giữ chế độ duyệt hoặc đổi manual/automatic. Áp dụng cần `revision` khớp với xem trước, tính lại trong khóa queue/content/SQLite.
- Giữ đúng nhóm và Page–Token binding. Lấy kho dùng source claim đã có, phân bổ cân bằng Pages. Không upload video/tạo Website trực tiếp tại endpoint.
- Không đẩy bài quá nửa đêm sang ngày mai. Overflow giữ lịch/claim cũ; báo số bài chưa xếp được. Replan để tránh chiếm slot cũ của overflow.
- Áp dụng cả nhóm hoặc lấy từ kho đặt `allocation_override_date` cho Daily cùng nhóm đến hết ngày, tránh worker tự lấp slot vừa dời bằng bài ngày mai. Daily tiếp tục từ ngày sau. Đổi lịch vài bài đã chọn không ngừng Daily của cả nhóm.
- Cập nhật SQLite slot và intake trước JSON; nếu JSON lỗi, khôi phục từ intent. Không thay nội dung, URL, trạng thái preparing, hoặc đánh dấu `draft_edited_at` chỉ vì đổi lịch; First Comment vẫn được điền khi Website hoàn tất.
- Bài đã freeze, có Meta ID, claim publish hoặc outcome chưa rõ không được đổi lịch. `schedule_day` ngăn bài hôm nay tự chuyển sang xuất bản ngày sau; bài chưa gửi Meta quay về Draft để hẹn lại. Không sửa lịch đã gửi Meta.
- Giao diện xem trước hiển thị ngày, giờ đầu/cuối, auto/manual, overflow. Sửa input hủy preview; auto-refresh tạm ngưng khi đang chọn bài/mở modal.

## Kiểm chứng và artifact

Đọc các report trong `checkpoints/evidence/v1.2.3/`: full suite, browser offline, replay snapshot thật và payload installer. Replay nằm riêng ở `support/v1.2.3/`, tuyệt đối không commit queue/binding/credential thật.
Bộ cài dự kiến `release/Highlight_Desktop_Test_Setup_v1.2.3.exe`; kết quả hash/source identity sẽ ghi trong `installer_verify.json` và checkpoint latest sau build. Tag `v1.2.3` chỉ tạo ở commit ứng dụng được đóng gói; các commit evidence sau có thể tiến nhánh.

## Session sau

1. Đọc `CODEX_CHECKPOINT_LATEST.md`, report deployment và installer; kiểm tra runtime `build_identity.json`, PID/port và worker hiện tại. Không coi bộ cài đã tạo là đã cài vào app đang chạy.
2. Trước nâng cấp, đóng app khi không có upload đang chạy, backup posts/ledger/config/content queue/credentials và source local ngoài repo. Dùng installer giữ dữ liệu; không seed queue mới lên queue cũ.
3. Trong Nhóm Trang chọn NEW → Cả nhóm hôm nay → Xem trước → Áp dụng. Chọn “Tự lên lịch khi sẵn sàng” nếu muốn tự đăng sau Website; manual cần duyệt Draft. Kho dùng “Lấy từ kho cho hôm nay”. Ngày/giờ thực tế lấy từ máy chạy app; không dùng 06/10 cố định ở session khác.
4. Bài Website chưa sẵn sàng có lịch hôm nay vẫn phải chờ chuẩn bị. Xem lỗi Website/English và retry đúng URL; không coi đã xếp lịch là đã xuất bản.
5. Giữ receipt các bài đã published và Meta IDs. `post_1791183298_90ab26` đã published/First Comment posted; không repost. Clip 262 bytes có replacement ngoài intake ở `support/v1.2.2/media-recovery/`; đọc checkpoint v1.2.2 trước import. Lỗi `368/4854002` còn cần xác minh Facebook.

## Build và GitHub

```powershell
$env:PATH = 'E:\OPENCLAW\BOB\Highlight destop test\bin;' + $env:PATH
python -m pytest -q --no-header
python checkpoints/tools/v1.2.3/offline_ui.py
python checkpoints/tools/v1.2.3/replay_schedule.py
powershell -NoProfile -ExecutionPolicy Bypass -File build_release.ps1 -Version 1.2.3 -SkipTests -ToolSource 'E:\OPENCLAW\BOB\Highlight destop test\bin' -RuntimeSource 'E:\OPENCLAW\BOB\Highlight destop test\runtime' -IconSource 'E:\OPENCLAW\BOB\Highlight destop test\app.ico' -WhisperModelSource 'E:\OPENCLAW\BOB\Highlight destop test\models\faster-whisper-small'
powershell -NoProfile -ExecutionPolicy Bypass -File checkpoints/tools/v1.2.3/verify_payload.ps1
```

Source phải sạch trước build. Credential GitHub chỉ đọc trong memory từ file đã có ở workspace; không in/commit credential. Helper giữ Git config kế thừa rồi thêm auth header trong memory. Khi có mạng, lần lượt chạy `python checkpoints/tools/v1.2.3/github_release.py inspect`, `push`, `draft`, `upload`, `publish`, `verify`. Ba asset: installer, SHA256, `CODEX_CHECKPOINT_v1.2.3.md`. Chỉ báo deploy thành công khi verify xác nhận tag/branch/digest và link tải công khai. Không bỏ qua hạn chế mạng của môi trường.
