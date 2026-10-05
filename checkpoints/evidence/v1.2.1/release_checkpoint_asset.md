# Checkpoint v1.2.1 — quản lý theo nhóm, Draft gọn và First Comment

Ngày: 2026-10-06 (Asia/Saigon)

Nhánh phát hành: `release/v1.2.1`; nhánh sửa ban đầu: `fix/v1.2.1-group-review`. Tag cố định `v1.2.1` trỏ tới source đóng gói `edfdd753800c0171e5758b25b9da8a3b96766df3`; identity `source_dirty=false`, version `1.2.1`. Các commit tiếp theo trên nhánh phát hành chỉ lưu tools/evidence/checkpoint, không đổi code runtime trong bộ cài. Không sửa tag/release cũ.

## Mốc phát hành và tài liệu session

- GitHub Release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.2.1
- Bộ cài: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.2.1/Highlight_Desktop_Test_Setup_v1.2.1.exe
- Checksum: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.2.1/Highlight_Desktop_Test_Setup_v1.2.1.sha256
- Checkpoint đính kèm: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.2.1/CODEX_CHECKPOINT_v1.2.1.md
- Checkpoint cập nhật cùng evidence: https://github.com/minhpark89/Highlight_Video_Studio/blob/release/v1.2.1/CHECKPOINT_V1_2_1_GROUP_REVIEW_20261006.md
- Source đúng bản đóng gói: https://github.com/minhpark89/Highlight_Video_Studio/tree/v1.2.1

Đây là kênh `desktop-test`, phát hành dưới dạng prerelease như v1.2.0. Checkpoint asset ghi trạng thái kiểm chứng trước phát hành; kết quả công khai cuối cùng được lưu tiếp trên nhánh `release/v1.2.1` trong `checkpoints/evidence/v1.2.1/release.json` và `public_download_verify.json`.

## Đã sửa

- Sửa bộ nhận diện ngôn ngữ Website: các câu tiếng Anh ngắn bị `langdetect` nhận nhầm thành Dutch/Catalan/Romanian không còn làm package lỗi. Nội dung tiếng Việt, Tây Ban Nha, Pháp, Nhật, Trung, Hàn, Nga, Ả Rập và đoạn trộn vẫn bị chặn.
- Khi Website đã tồn tại, kiểm tra toàn bộ bài public trước; nếu tiếng Anh hợp lệ thì giữ nguyên bài và YouTube embed, không sửa hoặc tạo bài mới. Nếu có đoạn ngoại ngữ thật thì sửa đúng URL CMS cũ rồi xác minh lại.
- First Comment không còn bị coi là lỗi độc lập khi Website chưa xác minh. Worker hoàn tất Website trước, sau đó mới tạo comment có đúng URL một lần và đưa vào hàng đợi retry nếu Meta chưa nhận.
- Pipeline hàng ngày xử lý Page/Token group đã chọn trước khi gọi content worker. Slot lưu bền vững; bài chuẩn bị có `page_id`, `page_name`, `group_id`, `token_id`, `token_group_id`, `scheduled_time` và chế độ giữ lịch. Token group liên kết được ưu tiên thay cho token mặc định của Page.
- Thêm `web/post_queries.py` và `/api/posts/list`: lọc theo trạng thái/nhóm/Page/Token trước khi enrich, phân trang tối đa 100 dòng. `/api/posts/<id>` tải riêng một Draft. Màn quản lý không còn gửi toàn bộ queue lớn trong mỗi lần refresh.
- Thêm màn **Chuẩn bị & Draft theo nhóm Page**: số video kho chờ, nhóm đang bật Post hàng ngày, Page/Token/giờ từng bài, lọc nhóm/Page/trạng thái, duyệt một bài hoặc nhiều bài, retry Website và chọn App giữ lịch hoặc Meta giữ lịch.
- Thống kê Token chỉ tải khi mở phần đối chiếu; danh sách lịch dùng trang 50 dòng.

## Kiểm chứng

- `581 passed, 3 skipped, 29 subtests passed`.
- Browser offline QA: `checkpoints/evidence/v1.2.1/ui_verify.json`; không có JavaScript error. Đã kiểm tra 800 clip kho, 65 Draft, 493 bài lịch sử, phân trang 50/30 dòng, duyệt batch 5 bài, tải detail riêng và lưu chế độ giữ lịch.
- Xác minh ba bài Website lỗi trên máy hiện tại: HTTP 200, không còn đoạn bị nhận nhầm, package cached là English, YouTube embed gốc tồn tại trên public article. Báo cáo: `checkpoints/evidence/v1.2.1/public_articles_verify.json`.
- Bộ cài: `release/Highlight_Desktop_Test_Setup_v1.2.1.exe`
- SHA-256 và source identity được xác minh ở `checkpoints/evidence/v1.2.1/installer_verify.json` và file `.sha256` cùng bộ cài.
- Bộ cài cuối: **705,059,328 bytes**; SHA-256 `d9b4378cd5ee8e0fe695d13a4a5e72fd16c847999769db40cb0d5f39a9c03fce`.
- Verifier đã đọc payload và đối chiếu **17 file runtime**, bao gồm `web/static/group_review.js`, `web/post_queries.py` và cả hai HTML; không có state, queue, token hoặc credential thật trong installer.
- Sau hai kiểm thử bổ sung, suite cuối: `581 passed, 3 skipped, 29 subtests passed`; fixture 800 bài chờ chứng minh vòng idle không viết lại Content queue hoặc posts queue. Kiểm thử luồng manual nhóm → claim Token group → Draft → duyệt batch → hàng chờ Meta cũng qua.

## Cách dùng

1. Mở tab **Nhóm Trang & Lên Lịch**, chọn nhóm và bật **Post hàng ngày**. Nhóm mới mặc định `Duyệt tay → Draft`; có thể chọn tự động nếu muốn worker giao Meta theo lịch. Giữ lựa chọn tự động đã lưu của nhóm cũ.
2. Vào khung **Chuẩn bị & Draft theo nhóm** trong cùng tab. Bài chỉ xuất hiện sau khi đã được gắn Page, Token và giờ; không cần tìm trong toàn bộ lịch sử.
3. Mở một bài để sửa, kiểm tra First Comment/Website, rồi **Duyệt & lên lịch**. Với Meta giữ lịch, app upload trước để Facebook tự đăng đúng giờ.
4. Nếu Website lỗi, dùng **Thử lại Website** trên đúng bài. Không tạo URL CMS mới và không gửi lại Reel.

Bộ cài chưa tự cài đè runtime đang chạy và chưa đăng/xóa bài Meta thật. Installer sao lưu dữ liệu và giữ queue, token/Page mapping, cấu hình, output/ledger khi nâng cấp. Sau cài, dùng **Thử lại Website** cho ba bài bị chặn; app xác minh lại đúng URL.

## Cách session sau tiếp tục fix

1. Đọc `CODEX_CHECKPOINT_LATEST.md`, checkpoint này và evidence trên nhánh `release/v1.2.1`. Lấy source bằng `git fetch origin --tags`, rồi tạo nhánh sửa mới từ `origin/release/v1.2.1`. Kiểm tra `git rev-parse 'v1.2.1^{commit}'` phải là `edfdd753800c0171e5758b25b9da8a3b96766df3`. Nếu cần tái hiện đúng bộ cài, checkout tag trong worktree riêng. Không di chuyển tag hoặc force-push nhánh phát hành.
2. Kiểm tra `build_identity.json` tại thư mục cài app đang chạy. Bộ cài có bản mới không có nghĩa app đã nâng cấp. Runtime được quan sát trước lượt phát hành nằm ở `E:\OPENCLAW\BOB\Highlight destop test`, từng có identity `1.1.9-meta-cancel1`; kiểm tra lại thay vì dùng giá trị cũ.
3. Xác định PID/port qua `%LOCALAPPDATA%\HighlightVideoStudio\run\runtime.json` hoặc runtime directory mà launcher thực tế đang dùng. Chỉ xuất `host`, `port`, `pid`, `started_at`, `url`; file có session token nên không dump toàn bộ. Đối chiếu PID và listening port trước khi gọi API. Port đổi sau restart, không mặc định dùng 5080. API cần session hiện tại trong bộ nhớ, không đưa token vào log/checkpoint.
4. Trước nâng cấp hoặc sửa dữ liệu, đóng app đúng cách rồi sao lưu thư mục cài/data, `posts.json`, `jobs.json`, config, Page/Token/group mapping, output và ledger SQLite cùng các file phụ liên quan. Giữ backup local có timestamp; không đưa backup chứa credential lên GitHub. Không sửa queue thủ công khi worker đang chạy.
5. Với ba post `post_1791183298_90ab26`, `post_1791183307_f38a00`, `post_1791183338_f1f62c`: nguyên nhân đã tìm là câu English ngắn bị `langdetect` nhận nhầm, làm Website chưa ready và chặn First Comment. Public article đã được đọc/xác minh, chưa xác nhận các Reel/comment lỗi đã đăng thành công. Dùng **Thử lại Website** tại đúng post, kiểm tra cùng URL/CMS ID và YouTube embed gốc. First Comment phải chứa URL đúng một lần. Giữ `comment_id`/receipt; comment đã posted thì không phát lại.
6. Với Draft/nhóm: kiểm tra nhóm đã bật **Post hằng ngày**, video kho hợp lệ, slot claim và các trường `page_id`, `group_id`, `token_id`, `token_group_id`, `scheduled_time`. Token Group liên kết phải khớp nhóm được chọn. Nhóm mới mặc định duyệt tay; nhóm cũ giữ chế độ đã lưu. Màn quản lý hiển thị 50 dòng/trang, review nhóm 30 dòng/trang; chuyển trang/lọc trước khi kết luận thiếu bài. Token audit chỉ tải khi mở đối chiếu.
7. Với lỗi Meta/MP4: đọc `CHECKPOINT_V1_2_0_20261005.md` và `CHECKPOINT_VIDEO_RECOVERY_20261005.md`. File 262 bytes/mốc cắt vượt EOF là lỗi media khác với Website. Dùng ffprobe kiểm tra video stream/duration và đọc đúng upload Video ID. Chỉ tạo lịch thay thế qua UI khi fresh diagnosis xác nhận lỗi terminal; giữ bài/Meta IDs cũ, ledger và receipt để tránh đăng trùng. Lỗi `368/4854002` cần quản trị viên xác minh Facebook, không coi bản này đã gỡ hạn chế.
8. Thu thập lỗi đã lọc credential: thao tác gây lỗi, identity/commit, post ID, mode App/Meta, Page/group/token IDs (không lấy token value), URL, timestamp/timezone, HTTP/code/subcode/trace ID, ffprobe và ảnh UI. Bổ sung vào checkpoint/evidence cùng nhánh sửa. Chạy test phù hợp lỗi, full suite trước bộ cài mới; dùng version/tag mới để giữ bản 1.2.1 tái hiện được.

Ví dụ kiểm tra identity/PID/port không in session token, sau khi xác nhận đường dẫn app:

```powershell
$appDirectory = 'E:\OPENCLAW\BOB\Highlight destop test'
Get-Content -Encoding UTF8 -LiteralPath (Join-Path $appDirectory 'build_identity.json')
$runFile = Join-Path $env:LOCALAPPDATA 'HighlightVideoStudio\run\runtime.json'
$sessionInfo = Get-Content -Encoding UTF8 -LiteralPath $runFile | ConvertFrom-Json
$sessionInfo | Select-Object host, port, pid, started_at, url
Get-Process -Id $sessionInfo.pid | Select-Object Id, ProcessName, Path
Get-NetTCPConnection -State Listen -OwningProcess $sessionInfo.pid | Select-Object LocalAddress, LocalPort, OwningProcess
```

## Lệnh kiểm tra và đóng gói

```powershell
$env:PATH = 'E:\OPENCLAW\BOB\Highlight destop test\bin;' + $env:PATH
python -m pytest -q --no-header
python checkpoints\tools\v1.2.1\offline_ui.py
.\build_release.ps1 -Version 1.2.1 -SkipTests -ToolSource 'E:\OPENCLAW\BOB\Highlight destop test\bin' -RuntimeSource 'E:\OPENCLAW\BOB\Highlight destop test\runtime' -IconSource 'E:\OPENCLAW\BOB\Highlight destop test\app.ico' -WhisperModelSource 'E:\OPENCLAW\BOB\Highlight destop test\models\faster-whisper-small'
powershell -NoProfile -File checkpoints\tools\v1.2.1\verify_payload.ps1
```
