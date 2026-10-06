# Latest checkpoint — v1.2.6 Content recovery

Ngày 2026-10-06. Đọc [CHECKPOINT_V1_2_6_CONTENT_RECOVERY_20261006.md](CHECKPOINT_V1_2_6_CONTENT_RECOVERY_20261006.md) trước khi sửa tiếp. Nhánh `release/v1.2.6`, Graph v24.0. Thumbnail ưu tiên model ảnh; hai ảnh body từ video dài gốc; text LLM có fallback; Website giữ URL, embed thật và comment đúng link; video lỗi terminal có phục hồi/xóa local qua fresh Meta check.

Kiểm tra cuối: **507 passed, 4 skipped, 29 subtests passed**, JavaScript syntax (4 inline + 1 external), templates identical. HTTP thật bị chặn trong offline tests. Chưa thay runtime/lịch/token thật. Build/payload hoàn tất: 705081856 bytes, SHA256 d9720eca0e476a3ee0c160b1d1f3a8fef96445bd8d74c0ef3b494e2cba61df8d, tag/source 15d5157d3ab3bf05ec5c1c6a2c08645d9d9ed643. GitHub đã public (Release ID 404495170); tải đầy đủ ba asset không đăng nhập đã khớp HTTP200/hash lúc 15:59:43 +07. Release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.2.6. Checkpoint asset kèm docs Meta và bundle source tại support/v1.2.6. Chưa cài vào runtime thật; dùng Thử lại Website / Kiểm tra Meta sau khi tự cài. Tool phát hành: `checkpoints/tools/v1.2.6/`. Không đổi tag/asset các release cũ.

## Checkpoint trước

# Checkpoint mới nhất — Highlight Desktop Test v1.2.5

Ngày 2026-10-06, Asia/Saigon. Nhánh `release/v1.2.5`. Đọc [CHECKPOINT_V1_2_5_META_BACKEND_20261006.md](CHECKPOINT_V1_2_5_META_BACKEND_20261006.md) và [docs/META_V24_BACKEND.md](docs/META_V24_BACKEND.md).

Theo yêu cầu người dùng, chuyển các luồng Meta của app từ Graph API v22.0 sang **v24.0**, rồi cập nhật backend theo tài liệu Meta về Page token/System User/NPE. Bản mới v1.2.5: refresh exact binding trước Init, cache 300 giây/lock theo credential, kiểm tra CREATE_CONTENT/MODERATE và scopes riêng, Bearer Graph/cursor pagination/OAuth rupload, pause 60 giây khi API access blocked và sanitized receipts. Giữ upload IDs/outcome_unknown và tránh đăng lại khi comment lỗi. Chưa thay scheduler/pacing hay live queue. Đã phát hành GitHub v1.2.5 và xác minh tải toàn bộ 3 asset; chưa cài app mới vào runtime, không chạy test chức năng/hồi quy.

Đã build và inspect payload local: `release/Highlight_Desktop_Test_Setup_v1.2.5.exe`, **705077760 bytes**, SHA256 `8194509413b225e4217231bc9441be406e2f18132c3b1b0f7395c3c3b53f53b0`. Tag v1.2.5/source commit `1bed062ae03f67fbedcfda468cbc818878830ba6`, identity sạch, Graph v24.0, khớp 19 source file, không có runtime state/credential. Evidence `checkpoints/evidence/v1.2.5/installer_payload.json`. Không chạy test hồi quy/chức năng, chưa tự cài vào runtime thật.

Người dùng đã yêu cầu phát hành v1.2.5 lên GitHub và xác nhận credential nhóm đang dùng để post đã hoạt động lại; nhóm token còn lại trong snapshot cũ không dùng để post, không cần xử lý trong đợt này. Đã công khai và xác minh 3 asset; không coi snapshot lỗi cũ là restriction còn cần mở khóa. Đọc checkpoint v1.2.5 để lấy full symptom/source map, bước thu thập lỗi, các guard cần giữ, official Meta docs và thứ tự tối ưu chưa triển khai.

## GitHub v1.2.5 đã phát hành và xác minh

Release ID `404429104`, `draft=false`, `prerelease=true`. [Trang tải](https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.2.5). Cả ba asset installer/SHA256/checkpoint đã tải toàn bộ không đăng nhập, khớp byte/hash lúc `2026-10-06T07:42:54.794420+00:00`. Evidence: `checkpoints/evidence/v1.2.5/release.json`, `deployment_status.json`, `public_download_verify.json`.

Source tag cố định `1bed062ae03f67fbedcfda468cbc818878830ba6`; nhánh `release/v1.2.5` có checkpoint/evidence mới hơn. Offline source: `E:\OPENCLAW\BOB\support\v1.2.5\Highlight_Source_v1.2.5_published.bundle`. Checkpoint asset độc lập chứa appendix docs Meta, giữ nguyên sau publish; trạng thái cuối ở checkpoint trên nhánh release. Phiên này không chạy test chức năng/hồi quy hoặc cài vào runtime thật.

## Bản phát hành trước — v1.2.3

Ngày 2026-10-06, Asia/Saigon. Nhánh `release/v1.2.3`. Đọc [CHECKPOINT_V1_2_3_TODAY_SCHEDULE_20261006.md](CHECKPOINT_V1_2_3_TODAY_SCHEDULE_20261006.md).

Thêm chọn preparing/Draft và xem trước/áp dụng lịch hôm nay cho bài chọn, cả nhóm, hoặc lấy kho vào nhóm Page. Giữ claim/Page–Token/nội dung, báo overflow trong ngày, không tràn ngày; Daily không tự lấp lịch ngày mai sau khi đã áp dụng cả nhóm hôm nay. Bài chưa sẵn sàng tiếp tục làm Website/First Comment; hết ngày phải hẹn lại. Bao gồm các sửa v1.2.2.

Kiểm thử **632 passed, 4 skipped, 29 subtests passed**. Browser offline **9 checks, không có JavaScript error**. Replay snapshot thật ở bản sao riêng: **294** bài NEW có lịch 06/10, **11:31–14:16**, giữ nội dung/trạng thái/binding/remote posts; xem trước lấy thêm 20 video từ kho. Preview cả nhóm mất khoảng 0.15 giây. Đây là replay, app thật vẫn chạy bản cũ, chưa thay queue hoặc gửi Meta/CMS.

Bộ cài đã kiểm chứng: `release/Highlight_Desktop_Test_Setup_v1.2.3.exe`, **705073152 bytes**, SHA256 `369bb5e8560faaaef74456a0e5ed7b9e05a8e041d20d1730f5da4ea7bdae3c02`. Tag source `v1.2.3` tại `8a5f77f0f5be55a8839e13b1542763b7d936438d`, identity sạch; payload khớp 21 file, không chứa state/credential người dùng. Xem `checkpoints/evidence/v1.2.3/installer_verify.json`.

**Đã phát hành GitHub v1.2.3:** Release ID `404324624`, `draft=false`, `prerelease=true`. [Trang tải](https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.2.3); ba asset installer/SHA256/checkpoint đã được tải toàn bộ không đăng nhập và đối chiếu hash với local lúc `2026-10-06T05:09:28.556307+00:00`. Tag remote/source đã xác minh. Evidence: `checkpoints/evidence/v1.2.3/release.json`, `deployment_status.json`, `public_download_verify.json`. Phiên deploy không nâng cấp runtime hoặc thay lịch thật.

Checkpoint chi tiết có bảng triệu chứng → file source/test, cách lấy source từ nhánh `release/v1.2.3`, giữ claim/Meta IDs và tái hiện lỗi trên bản sao. Source app trong tag/installer là commit `8a5f77f0f5be55a8839e13b1542763b7d936438d`; nhánh phát hành có checkpoint/tooling mới hơn. Source backup offline ở `E:\OPENCLAW\BOB\support\v1.2.3\Highlight_Source_v1.2.3_published.bundle`; binary installer và asset ở `source-worktree/release/`.

Lỗi WinError 10013 và chẩn đoán network trong checkpoint là lịch sử phiên trước. Trạng thái mới dùng `checkpoints/evidence/v1.2.3/deployment_status.json`; helper `checkpoints/tools/v1.2.3/deploy_github.ps1` hỗ trợ resume, kiểm tra digest và không thay asset đã public.

## Checkpoint trước — v1.2.2

Ngày: 2026-10-06, Asia/Saigon. Xem [CHECKPOINT_V1_2_2_META_RECOVERY_20261006.md](CHECKPOINT_V1_2_2_META_RECOVERY_20261006.md).

Bản sửa thêm retry Init chắc chắn bị từ chối qua App, Sync Page/Token đọc lại Meta ID, cảnh báo lịch Meta quá giờ, chuyển cache text-only sang Website cho Daily và cách ly package non-English để pipeline tiếp tục. Full suite **608 passed, 4 skipped, 29 subtests passed**; browser offline **7 checks, không có JavaScript error**. Evidence: `checkpoints/evidence/v1.2.2/`.

Tag local `v1.2.2` tại source commit `e5fa37306e2c9214f0012ff36784bd8c629f44e7`; nhánh `release/v1.2.2`. Bộ cài: `release/Highlight_Desktop_Test_Setup_v1.2.2.exe`, 705064448 bytes; SHA256 `bb86ce8047a17acd0109792e65fbe8895421cc27eec1df116f5e2475a67a323d`. Payload khớp 20 file source, identity sạch, không chứa state/credential người dùng. Xem `installer_verify.json`.

**Chưa deploy lên GitHub.** GitHub API bị chặn (`WinError 10013`); Git push cũng thất bại và kiểm tra remote báo `Failed to connect to github.com port 443`. Chưa tạo/public release v1.2.2. `checkpoints/evidence/v1.2.2/deployment_status.json` ghi trạng thái này. Installer, SHA256 và checkpoint asset đã sẵn sàng local. Giữ nguyên release/tag v1.2.1. Chưa cài vào runtime đang dùng hoặc đăng/xóa Meta/CMS thật.

Source backup offline: `E:\OPENCLAW\BOB\support\v1.2.2\Highlight_Source_v1.2.2.bundle`, chứa nhánh `release/v1.2.2` và tag `v1.2.2`. Session sau dùng repo hiện tại hoặc clone bundle vào thư mục mới; khi GitHub hoạt động, chạy các bước inspect/push/draft/upload/publish/verify ở checkpoint chi tiết. Deployment helper mới giữ nguyên cấu hình Git kế thừa của sandbox rồi thêm auth header trong bộ nhớ; không đưa credential vào source/log.

Session sau đọc checkpoint v1.2.2 để lấy lệnh build/publish và cách xử lý từng loại lỗi; kiểm tra identity/PID/port, backup local trước nâng cấp, giữ Meta IDs/comment receipts/ledger. Bài `post_1791183298_90ab26` đã published; không đăng lại. Lỗi `368/4854002` vẫn cần xác minh Facebook.

Đối chiếu bổ sung 10:35–10:39: replay bản sao dữ liệu thật giúp 273 bài tiếp tục chuẩn bị, cách ly 10 gói non-English; 100 cặp Page–Token qua preflight binding đã lưu và 300 MP4 Daily qua ffprobe. Runtime thật chưa thay đổi. Đã render MP4 thay thế 55 giây cho clip 262 bytes ở ảnh 1, đặt ngoài output intake tại `support/v1.2.2/media-recovery/`; chưa gửi Meta. Đọc phần bổ sung trong checkpoint chi tiết và các report `*_verify.json` trước khi import/thay thế. Source backup mới: `support/v1.2.2/Highlight_Source_v1.2.2_runtime-audit.bundle`.

## Bản phát hành trước — v1.2.1

Ngày: 2026-10-06 (Asia/Saigon). Nhánh phát hành: `release/v1.2.1`. Tag source: `v1.2.1` tại `edfdd753800c0171e5758b25b9da8a3b96766df3`.

Đọc [CHECKPOINT_V1_2_1_GROUP_REVIEW_20261006.md](CHECKPOINT_V1_2_1_GROUP_REVIEW_20261006.md): sửa nhận diện sai câu tiếng Anh làm Website/First Comment bị chặn; chuẩn bị và Draft theo nhóm có Page/Token/giờ; mặc định duyệt tay; giữ lịch Meta upload trước; phân trang 50/30 dòng; worker kho không ghi lại 800 bài khi không có thay đổi.

Kiểm thử: **581 passed, 3 skipped, 29 subtests passed**. Browser không có JavaScript error. Ba bài Website thực tế đã đọc lại HTTP 200 và xác minh English/YouTube gốc. Bộ cài local: `release/Highlight_Desktop_Test_Setup_v1.2.1.exe`; evidence mới ở `checkpoints/evidence/v1.2.1/`. Đã phát hành GitHub (Release ID `404026464`, `draft=false`, `prerelease=true`); ba asset, digest, tag và link tải không đăng nhập đã xác minh. Chưa cài đè runtime người dùng hoặc đăng/xóa bài Meta thật.

Release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.2.1. Checkpoint đính kèm: `CODEX_CHECKPOINT_v1.2.1.md`. Session sau đọc checkpoint trên nhánh phát hành, xác định identity/PID/port, sao lưu dữ liệu rồi retry đúng post/Website URL; giữ Meta IDs, comment receipt và ledger để tránh đăng trùng.

## Bản phát hành trước — v1.2.0

Ngày: 2026-10-05, Asia/Saigon. Nhánh: `release/v1.2.0`. Tag cố định: `v1.2.0`.

Đọc [CHECKPOINT_V1_2_0_20261005.md](CHECKPOINT_V1_2_0_20261005.md) trước khi sửa lỗi tiếp. Tài liệu ghi yêu cầu cuối cùng, nguyên nhân MP4 262 bytes, sửa Website cùng URL, quy trình tạo lịch thay thế, lệnh build/test và cách giữ dữ liệu/Meta IDs.

- Release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.2.0
- Installer: https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.2.0/Highlight_Desktop_Test_Setup_v1.2.0.exe
- Full pytest: **567 passed, 3 skipped, 29 subtests passed**.
- Source đóng gói: `a199630d39d636e0c1b9173f12691cf2da1436a8`; tag `v1.2.0` cố định ở commit này.
- Release ID `403796965` đã công khai (`prerelease=true`); ba asset và link tải không đăng nhập đã xác minh.
- Evidence phát hành cuối: `checkpoints/evidence/v1.2.0/`.

Website giữ embed video YouTube gốc dài; kho/output được phân bổ cho nhóm/Page tick **Post hằng ngày**, upload trước để Facebook giữ lịch. Lỗi terminal Meta được phục hồi qua UI với MP4 đã sửa và giờ mới, giữ bài/ID cũ. Website retry sửa đúng URL cũ.

Chưa cài bản này vào runtime đang dùng hoặc đăng lại các bài Meta/CMS thật trong lượt phát hành. Session sau kiểm tra `build_identity.json` của app đang chạy trước, rồi đọc diagnosis đúng Video ID.

Checkpoint lịch sử `v1.1.9-autopublish5` vẫn ở `release/CODEX_CHECKPOINT_v1.1.9-autopublish5.md`. Hai lỗi `368/4854002` yêu cầu quản trị viên xác minh danh tính trên Facebook; không coi là lỗi MP4 hoặc đã được giải quyết bởi bản mới.
