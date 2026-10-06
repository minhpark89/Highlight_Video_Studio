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
Bộ cài đã kiểm chứng `release/Highlight_Desktop_Test_Setup_v1.2.3.exe`, 705073152 bytes; SHA256 `369bb5e8560faaaef74456a0e5ed7b9e05a8e041d20d1730f5da4ea7bdae3c02`. Tag source `v1.2.3` cố định tại `8a5f77f0f5be55a8839e13b1542763b7d936438d`, identity sạch, 21 file payload khớp, không có state/credential người dùng. Full suite **632 passed, 4 skipped, 29 subtests passed**; browser **9 checks**, không có JavaScript error. Các commit evidence sau có thể tiến nhánh. Tag v1.2.1/v1.2.2 không đổi.

Replay snapshot 11:00 riêng đã xếp **294** bài NEW còn preparing/Draft về 06/10 **11:31–14:16**, 0 overflow/skip; 198 bài trước đó ở 07/10. Giữ status, caption, First Comment, Website URL, Page–Token, source claim và mọi bài không chọn/remote. Preview cả nhóm 0.1472 giây; lấy kho 20 bài có lịch đúng nhóm/ngày. Đây là kết quả offline, không thay lịch thật hoặc gửi Meta/CMS. Runtime cài đặt vẫn v1.2.1.

**Chưa deploy GitHub:** inspect API và Git remote vẫn thất bại kết nối port 443. Đọc `deployment_status.json` cho lần push cuối. Chưa tạo draft/public release v1.2.3, chưa có link tải công khai mới; bộ cài/SHA256/checkpoint asset đã sẵn sàng local. Không dùng URL dự đoán như URL đã xác minh.

Backup source offline: `E:\OPENCLAW\BOB\support\v1.2.3\Highlight_Source_v1.2.3.bundle`. Bundle chứa `release/v1.2.3` và `v1.2.3`; có thể clone vào thư mục mới trong workspace để sửa tiếp. Giữ `source-worktree/release/` vì binary installer và asset ignored không nằm trong bundle. Không cài đè hoặc sửa queue live trong session này.

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

## Tiếp tục deploy bằng đúng token đã chỉ định

Token được đọc từ **`E:\OPENCLAW\BOB\token github.txt`** bằng helper ngay từ lần deploy trước; không cần thay token vào source hoặc URL remote. Lần kiểm tra lại sau yêu cầu dùng token xác nhận đọc file/nhận dạng token thành công. DNS cả `github.com` và `api.github.com` hoạt động. Tạo TCP socket đến port 443 của cả hai trả `PermissionError`, errno=13, **WinError 10013**. Request `/user` có Bearer token cũng dừng ở cùng lỗi socket, chưa nhận HTTP response. Vì vậy chưa thể kết luận token hết hạn/thiếu quyền; chưa xảy ra kiểm tra xác thực ở phía GitHub. Không mô tả đây là GitHub ban tài khoản. Evidence: `network_diagnosis.json` và `deployment_status.json`.

Session trước thực sự đã phát hành v1.2.1: Release ID `404026464`, kiểm tra public asset lúc `2026-10-06T02:06:56+07:00`; `checkpoints/evidence/v1.2.1/release.json` có URL và digest đã xác minh. Điều đó không chứng minh quyền kết nối của phiên hiện tại giống phiên cũ. Phiên hiện tại có mạng hạn chế và không cho nâng quyền; không đổi proxy/TLS, mở background process ngoài sandbox hoặc dùng runtime khác để lách chặn.

Chạy lệnh sau **khi môi trường cho phép kết nối GitHub**, tại repo `E:\OPENCLAW\BOB\source-worktree`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File checkpoints/tools/v1.2.3/deploy_github.ps1
```

Helper `deploy` thực hiện các bước theo thứ tự, dừng ngay khi lỗi:

1. `inspect`: gọi `/user` bằng đúng token, đọc quyền push repo và tình trạng release v1.2.3. Nếu HTTP 401/403 thật sự được trả về thì lúc đó mới xử lý token/quyền.
2. `push`: kiểm tra source sạch, hash/size installer khớp proof, tag local đúng commit đóng gói; push atomic nhánh `release/v1.2.3` và tag `v1.2.3`, không force. Tag app cố định ở `8a5f77f0f5be55a8839e13b1542763b7d936438d`; HEAD nhánh có thể là commit checkpoint mới hơn.
3. Nếu chưa có release: tạo draft. Nếu có: `resume` kiểm tra tag remote khớp packaged commit, từng asset hiện có khớp tên/size/digest local rồi phục hồi metadata local. Không thay asset khác nội dung. Nếu release đã public, đi thẳng verify sau resume.
4. Với draft, upload đủ 3 asset rồi kiểm tra **cả 3** size/digest/state trước publish. `release/CODEX_CHECKPOINT_v1.2.3.md` đã chuẩn bị; không chỉnh lại asset sau khi upload nếu muốn resume không đổi digest. Checkpoint trong source có thể cập nhật riêng sau đó.
5. `verify`: kiểm tra release public, đúng 3 tên asset, tag/branch, digest và HTTP HEAD tải công khai không đăng nhập. Chỉ sau bước này cập nhật checkpoint thành deploy thành công và đưa link tải cho người dùng.

Các action lẻ vẫn chạy được để chẩn đoán: `python checkpoints/tools/v1.2.3/github_release.py <action>` với action `inspect`, `push`, `draft`, `resume`, `upload`, `publish`, `verify`. Metadata ignored tại `release/v1.2.3_release.json`; không có metadata không có nghĩa release chưa tồn tại, phải inspect/resume trước. Không tạo release khác để che lần dở dang.

Kiểm thử tooling bổ sung: `python -m pytest tests/test_github_deploy.py -q --no-header` → **5 passed**. App installer/source/tag đã kiểm chứng giữ nguyên; không cần build lại vì chỉ sửa công cụ deploy ngoài payload. Source backup bundle được cập nhật cùng nhánh checkpoint mới. Chưa nâng cấp runtime, chưa dời lịch thật hoặc gửi Meta/CMS trong lần thử deploy này.

## Chẩn đoán cấu hình quyền mạng

Không có HTTP_PROXY/HTTPS_PROXY/ALL_PROXY trong environment; WinHTTP dùng Direct access. Đọc firewall profile bị Access denied (`0x80041003`), nên chưa khẳng định được rule Windows Firewall cụ thể. Không tắt firewall, đổi proxy hoặc sửa token.

Đã đọc riêng các khóa liên quan quyền ở `C:\Users\PV\.codex\config.toml` và `E:\OPENCLAW\CodexData\config.toml`: cả hai đặt `sandbox_mode = "workspace-write"`, `approval_policy = "never"`, `[windows] sandbox = "elevated"`, chưa có `[sandbox_workspace_write] network_access`. Chính sách được cung cấp cho phiên hiện tại xác nhận network restricted và không cho nâng quyền. Không thể suy ra file nào đang điều khiển UI chỉ từ việc cả hai tồn tại; cần xác định cách người dùng mở Codex trước khi chỉ file cần sửa. Evidence: `network_config_findings.json`.

Hướng sửa là cấp quyền network cho phiên Codex qua cấu hình/quản lý quyền hợp lệ, giữ giới hạn filesystem. Thiết lập workspace-write cần xem xét là `[sandbox_workspace_write] network_access = true`; nếu dùng permission profile được ứng dụng/administrator quản lý, profile phải cho phép kết nối GitHub. Chưa chỉnh config global vì các file nằm ngoài workspace được phép ghi. Chưa tải được trang OpenAI Docs do kết nối cũng bị từ chối; chưa xác minh vị trí/nội dung nút UI cho phiên bản app này. Sau khi người dùng đổi cấu hình hợp lệ, mở phiên nhận quyền mới rồi kiểm tra lại `/user`; chỉ tiến hành deploy khi có HTTP response và quyền push.
