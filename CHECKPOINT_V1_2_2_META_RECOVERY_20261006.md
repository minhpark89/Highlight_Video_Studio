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

**Chưa deploy GitHub:** API bị môi trường chặn (`WinError 10013`); Git push thất bại ở kết nối và `git ls-remote` báo `Failed to connect to github.com port 443`. Chưa tạo draft/public release v1.2.2. Bộ cài, SHA256 và checkpoint asset đã chuẩn bị local. Xem `checkpoints/evidence/v1.2.2/deployment_status.json`. Không dùng URL v1.2.2 như link tải đã hoạt động cho đến khi có bằng chứng công khai.

Backup source offline: `E:\OPENCLAW\BOB\support\v1.2.2\Highlight_Source_v1.2.2.bundle`, chứa nhánh/tag mới và checkpoint. Có thể `git clone -b release/v1.2.2` từ bundle vào thư mục mới trong workspace rồi đặt origin về URL repo ở đầu tài liệu. Giữ repo hiện tại để tiếp tục deploy vì bundle clone không có installer/asset ignored. Source tag cố định ở commit ứng dụng; nhánh có thêm commit bằng chứng và sửa deployment helper để giữ cấu hình Git kế thừa, gồm safe.directory.

## Chẩn đoán runtime đã có trước phát hành

App tại `E:\OPENCLAW\BOB\Highlight destop test` đang chạy v1.2.1, commit `edfdd753800c0171e5758b25b9da8a3b96766df3`, `source_dirty=false`. PID/port chỉ là quan sát phiên cũ (launcher 19596, Python 11088, port 62711); session mới phải tự đối chiếu lại.

- Snapshot: 580 published, 11 processing, 12 meta_scheduled, 738 preparing, 90 draft.
- `post_1791183298_90ab26` (**Dominating Bodycam...**) đã published, Reel ID `2459387687888190`. Giữ receipt, không đăng lại bài này.
- Video ID `1456548559709071`: 262 bytes, Meta video_status=error, processing complete, publishing not_started. Đây là MP4 không có video hợp lệ. Dùng luồng thay video đã sửa khi diagnosis mới xác nhận terminal; không Finish file này.
- Lỗi `368 / 4854002` yêu cầu quản trị viên xác minh danh tính/quyền xuất bản trên Facebook. Bản sửa không tự gỡ hạn chế tài khoản.
- Một số Meta native schedule quá giờ; fresh read trả HTTP 400/API access blocked. Sync đúng Page/Token và đọc lại ID trước khi quyết định phục hồi. Không dựa vào giờ quá hạn để kết luận Reel chưa đăng.
- Daily plan `grp_1791020096_3`: enabled/daily=true, automatic, meta_scheduled, slots `04:00`, `10:50`, 2 bài/ngày, stagger 15 phút, từ `2026-10-06`. Cấu trúc hợp lệ; runtime v1.2.1 bị backlog 856/200 và lỗi cache `article_html contains a non-English paragraph` chặn pipeline. Các sửa trên được kiểm chứng bằng fixture, chưa cài vào runtime này hoặc đăng/xóa Meta/CMS thật.

## Session sau tiếp tục sửa lỗi

### Đối chiếu runtime và MP4 bổ sung, 2026-10-06 10:35–10:39

Ứng dụng vẫn chạy v1.2.1. Snapshot mới có 580 published, 8 processing, 15 meta_scheduled, 738 preparing và 90 draft. Không dùng số đếm trước đó như trạng thái hiện tại; worker thật vẫn hoạt động.

Đã replay hai chu kỳ v1.2.2 trên bản sao riêng, chặn mọi request mạng và giữ queue thật nguyên trạng. 273 bài preparing chuyển sang scheduled trong bản sao; 10 package ready có paragraph non-English được cách ly failed và giữ Website URL cũ. 300 bài của Daily plan có đủ Page/Token/giờ, đều thuộc nhóm đã chọn. Đọc riêng binding thật đã lưu: 100/100 cặp Page–Token qua preflight. Đọc riêng MP4 thật bằng ffprobe: 300/300 file hợp lệ. Đây là bằng chứng về phân bổ và áp dụng cache; không chứng minh đã xuất bản Meta hoặc đã nâng cấp runtime. Bản sao không có media output nên pressure/backlog của replay không đại diện backlog thật. Xem `runtime_replay_verify.json`, `daily_bindings_verify.json`, `daily_media_verify.json`.

Ảnh 1: source thật `downloads/job_1790748353_7c7164.mp4` dài **129.613787s**; clip cũ cắt **210–268s** nên file `job_1790748353_7c7164_clip_2.mp4` chỉ **262 bytes**. Saved Meta observation HTTP 200 xác nhận video error, processing complete, publishing not_started. Đã render MP4 thay thế local bằng renderer đã sửa, mốc **37.31–92.31s**, 9:16, 1080×1920, nền mờ giữ toàn khung game, audio gốc, không thêm subtitle. File dài **55.033008s**, 30265431 bytes, SHA256 `2c3d057faeeae5104f240212473d3d47f801380ce3b68a75ff25b4d12abae252`.

Asset local: `E:\OPENCLAW\BOB\support\v1.2.2\media-recovery\job_1790748353_7c7164_clip_2_recovered.mp4`. Giữ nguyên hash/file 262 bytes, post và Video ID `1456548559709071`; MP4 mới nằm ngoài output intake, chưa được import vào queue hoặc gửi Meta. Xem receipt `replacement_verify.json` trong evidence và thư mục media-recovery. Khi nhập asset để tạo lịch thay thế, tạm dừng intake trước để tránh worker Daily nhận file trước thao tác thay thế; fresh diagnosis phải vẫn xác nhận terminal đúng ID. UI dùng tên file MP4 trong output, nên cần import/copy có kiểm soát rồi dùng **Tạo lịch lại bằng video đã sửa**, chọn giờ mới và tiếp tục giữ bài/receipt cũ.

Ảnh 2: đã xác nhận post `post_1791183298_90ab26` là published và First Comment **posted**. Ảnh 3: ba Video IDs `1778638966517308`, `844950208675218`, `1419917729556034` còn meta_scheduled và observation HTTP 400 `API access blocked`. Bản mới xác định schedule_overdue; cần Sync đúng Token/Page và fresh read. Saved binding hợp lệ không chứng minh Graph API hiện có quyền đọc/xuất bản đối tượng.

Source backup bổ sung chứa checkpoint/evidence mới: `E:\OPENCLAW\BOB\support\v1.2.2\Highlight_Source_v1.2.2_runtime-audit.bundle`. Bộ cài/tag ứng dụng vẫn giữ nguyên commit đã kiểm chứng; commit bổ sung chỉ là bằng chứng và hướng dẫn phục hồi.

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
