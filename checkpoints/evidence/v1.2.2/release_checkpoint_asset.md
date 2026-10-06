# Checkpoint v1.2.2 — Meta recovery và chuẩn bị lịch hằng ngày

Ngày: 2026-10-06, Asia/Saigon. Repository: https://github.com/minhpark89/Highlight_Video_Studio.
Nhánh làm việc ban đầu: `fix/v1.2.2-meta-recovery`; nhánh phát hành local: `release/v1.2.2`; tag local: `v1.2.2` tại `e5fa37306e2c9214f0012ff36784bd8c629f44e7`.
Giữ nguyên tag/release `v1.2.1` tại `edfdd753800c0171e5758b25b9da8a3b96766df3`.

## Kết quả sửa và kiểm chứng

- Thêm **Đăng lại bằng App** cho lỗi preflight/Init bị từ chối chắc chắn, chưa có Meta ID. Endpoint chỉ xếp hàng, worker kiểm tra Page/Token trước khi đăng. Kiểm tra MP4, Website ready, English và First Comment chứa đúng một URL. Chặn ID Meta cũ, kết quả chưa rõ và video đã có bài/lịch khác trên cùng Page; lưu lỗi/giờ cũ trong `publish_retry_history`.
- Lịch Meta quá giờ hơn 90 giây hiển thị đỏ và mở diagnosis đúng Video ID. Có **Đồng bộ quyền và kiểm tra lại**, hoạt động độc lập với chu kỳ publisher. Sync chọn Token gốc hoặc binding đã xác minh, đọc lại cùng ID, giữ trạng thái/receipt và không gọi Finish/upload/comment. Phục hồi xuất bản qua luồng giữ nguyên ID đã có chốt chống gửi lặp.
- Cache text-only được chuyển sang tạo Website khi luồng chuẩn bị hằng ngày yêu cầu. Một package ready chứa non-English được cách ly thành failed, giữ URL cũ để sửa; những package hợp lệ phía sau tiếp tục xử lý.
- Khung chuẩn bị/Draft theo nhóm hiển thị pipeline sống/dừng, backlog và lỗi nội dung. Backlog chỉ tạm dừng render/intake mới; không có nghĩa lịch đã phân bổ hoặc content worker phải ngừng.
- Hai test cũ đã được cô lập: hardware cache ở thư mục tạm, CMS lookup giả lập HTTP 404. Không ghi cache người dùng hoặc gọi Website thật trong test offline này.
- Full suite: **608 passed, 4 skipped, 29 subtests passed**, chạy `python -m pytest -q --no-header`. Kiểm thử trọng tâm trước đó: **70 passed, 1 skipped**.
- Browser offline: 7 checks, không có JavaScript error; kết quả và ảnh trong `checkpoints/evidence/v1.2.2/`.
- Bộ cài local: `release/Highlight_Desktop_Test_Setup_v1.2.2.exe`, 705064448 bytes. SHA256: `bb86ce8047a17acd0109792e65fbe8895421cc27eec1df116f5e2475a67a323d`. Payload khớp 20 file source, version=1.2.2, source commit=`e5fa37306e2c9214f0012ff36784bd8c629f44e7`, source_dirty=false, không có state/credential người dùng. Xem `installer_verify.json`.

## Trạng thái phát hành

GitHub API kiểm tra quyền đã bị môi trường chặn kết nối (`WinError 10013`). Bộ cài, SHA256 và checkpoint asset đã chuẩn bị local; chưa có xác minh push/public release v1.2.2. Đọc `CODEX_CHECKPOINT_LATEST.md` và `deployment_status.json` để biết trạng thái cuối cùng. Không dùng URL v1.2.2 như link tải đã hoạt động cho đến khi có bằng chứng công khai.

## Chẩn đoán runtime đã có trước phát hành

App tại `E:\OPENCLAW\BOB\Highlight destop test` đang chạy v1.2.1, commit `edfdd753800c0171e5758b25b9da8a3b96766df3`, `source_dirty=false`. PID/port chỉ là quan sát phiên cũ (launcher 19596, Python 11088, port 62711); session mới phải tự đối chiếu lại.

- Snapshot: 580 published, 11 processing, 12 meta_scheduled, 738 preparing, 90 draft.
- `post_1791183298_90ab26` (**Dominating Bodycam...**) đã published, Reel ID `2459387687888190`. Giữ receipt, không đăng lại bài này.
- Video ID `1456548559709071`: 262 bytes, Meta video_status=error, processing complete, publishing not_started. Đây là MP4 không có video hợp lệ. Dùng luồng thay video đã sửa khi diagnosis mới xác nhận terminal; không Finish file này.
- Lỗi `368 / 4854002` yêu cầu quản trị viên xác minh danh tính/quyền xuất bản trên Facebook. Bản sửa không tự gỡ hạn chế tài khoản.
- Một số Meta native schedule quá giờ; fresh read trả HTTP 400/API access blocked. Sync đúng Page/Token và đọc lại ID trước khi quyết định phục hồi. Không dựa vào giờ quá hạn để kết luận Reel chưa đăng.
- Daily plan `grp_1791020096_3`: enabled/daily=true, automatic, meta_scheduled, slots `04:00`, `10:50`, 2 bài/ngày, stagger 15 phút, từ `2026-10-06`. Cấu trúc hợp lệ; runtime v1.2.1 bị backlog 856/200 và lỗi cache `article_html contains a non-English paragraph` chặn pipeline. Các sửa trên được kiểm chứng bằng fixture, chưa cài vào runtime này hoặc đăng/xóa Meta/CMS thật.

## Session sau tiếp tục sửa lỗi

1. Đọc `CODEX_CHECKPOINT_LATEST.md` rồi checkpoint này. Đối chiếu `git status`, nhánh, tag và `build_identity.json`; evidence `installer_verify.json` chứa commit source chính xác của bộ cài. Không di chuyển tag cũ hoặc force-push.
2. Xác định runtime theo `%LOCALAPPDATA%\HighlightVideoStudio\run\runtime.json`, chỉ đọc host/port/pid/started_at/url ra báo cáo. Không in session token. Đối chiếu PID và listening port, không mặc định 5080/62711.
3. Trước nâng cấp hoặc sửa dữ liệu, đóng app đúng cách rồi backup local: thư mục cài/data, posts/jobs/config, Page/Token/group mappings, output, ledger SQLite và sidecars. Không chỉnh queue khi worker chạy; không đưa backup/credential lên GitHub.
4. Lỗi Init chưa có ID: sửa quyền Token/Page và Website/comment rồi dùng **Đăng lại bằng App** một lần. Bài có ID hoặc outcome_unknown: mở **Kiểm tra Meta**, Sync đúng Token; chỉ dùng thao tác phục hồi video hiện có khi fresh read và UI cho phép. Giữ IDs/history/receipt.
5. Lịch Meta quá giờ: Sync và đọc lại cùng ID. Nếu published thì chờ worker đối soát permalink/comment. Nếu API blocked hoặc identity_required, kiểm tra Meta Business Suite và tài khoản quản trị. Không upload lại để vượt lỗi quyền.
6. Nhóm Daily: kiểm tra enabled, approval mode, slots, `page_id/group_id/token_id/token_group_id/scheduled_time`, package/Website trạng thái và cảnh báo pipeline. Với package failed, **Thử lại Website** trên đúng bài/URL cũ. Xác nhận English và YouTube embed gốc, First Comment chứa URL đúng một lần.
7. Lưu evidence đã lọc bí mật: thao tác, version/commit, post ID, App/Meta mode, Page/Token IDs (không token value), thời gian/timezone, HTTP/code/subcode/trace, ffprobe và ảnh UI. Thêm regression test tái hiện lỗi, chạy full suite rồi phát hành version mới.

## Build và phát hành có thể tiếp tục

```powershell
$env:PATH = 'E:\OPENCLAW\BOB\Highlight destop test\bin;' + $env:PATH
python -m pytest -q --no-header
python checkpoints\tools\v1.2.2\offline_ui.py
powershell -NoProfile -ExecutionPolicy Bypass -File build_release.ps1 -Version 1.2.2 -SkipTests -ToolSource 'E:\OPENCLAW\BOB\Highlight destop test\bin' -RuntimeSource 'E:\OPENCLAW\BOB\Highlight destop test\runtime' -IconSource 'E:\OPENCLAW\BOB\Highlight destop test\app.ico' -WhisperModelSource 'E:\OPENCLAW\BOB\Highlight destop test\models\faster-whisper-small'
powershell -NoProfile -ExecutionPolicy Bypass -File checkpoints\tools\v1.2.2\verify_payload.ps1
```

GitHub tools đọc credential local vào bộ nhớ, không log/commit token. Khi đã có source sạch/tag khớp bộ cài và mạng GitHub hoạt động:

```powershell
python checkpoints\tools\v1.2.2\github_release.py inspect
python checkpoints\tools\v1.2.2\github_release.py push
python checkpoints\tools\v1.2.2\github_release.py draft
python checkpoints\tools\v1.2.2\github_release.py upload
python checkpoints\tools\v1.2.2\github_release.py publish
python checkpoints\tools\v1.2.2\github_release.py verify
```

Đối chiếu release metadata và không tạo lại draft nếu đã tồn tại. Upload giữ draft cho đến đủ installer, SHA256 và checkpoint. Copy metadata cuối vào `checkpoints/evidence/v1.2.2/release.json`, chạy `verify_public_download.py` không xác thực, commit bằng chứng và push nhánh phát hành. Trạng thái GitHub cuối phải đọc trong checkpoint mới nhất; có bộ cài local không đồng nghĩa đã công khai release.
