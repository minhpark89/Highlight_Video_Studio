# Checkpoint v1.2.5 — Meta v24 và Page credential backend

Ngày 2026-10-06, Asia/Saigon. Nhánh `release/v1.2.5`; kế thừa v1.2.4 chuyển Graph v22 → v24. Người dùng yêu cầu kiểm tra đúng docs Meta về System User/New Pages Experience và đưa phần phù hợp vào backend như MXH.

## Tài liệu và thay đổi

Đọc [docs/META_V24_BACKEND.md](docs/META_V24_BACKEND.md) để xem nguồn chính thức, yêu cầu scope/task, App Review/access level, App Secret và các giới hạn chưa xác định được.

- Làm mới đúng credential/Page trước Init, cache tối đa 300 giây và lock riêng mỗi credential; discovery lỗi giữ 60 giây rồi cho làm mới lại, không dùng Page token cũ để bắt đầu upload.
- Page token phải có binding/fingerprint đúng root token_id và Page ID. Auto sync không đổi canonical credential sang token khác.
- CREATE_CONTENT và MODERATE được kiểm tra riêng; MANAGE không được coi là chứng minh quyền đăng/bình luận. Scope đọc được thì kiểm tra thiếu; không đọc được ghi unverified. /me chỉ là identity health, không phải bằng chứng đăng được.
- Graph auth dùng Bearer header; pagination qua cursor endpoint v24. Rupload giữ OAuth/octet-stream theo docs; ràng buộc đúng HTTPS host và không theo redirect.
- API access blocked dừng lượt gửi mới cùng credential 60 giây. Init/Finish giữ sanitized receipt. Không làm lại Reel khi comment lỗi; comment kết quả không rõ/HTTP5xx giữ outcome_unknown.
- Giữ scheduler/pacing/lịch và Meta upload IDs hiện tại. Các đề xuất tăng tốc scheduler chưa được triển khai trong bản này.

## Quyền tác động

Giai đoạn build chỉ sửa source-worktree và tạo artifact local. Sau đó người dùng đã yêu cầu **deploy v1.2.5 lên GitHub để tự tải/cài chạy lại**, kèm checkpoint cho LLM session sau. Phạm vi deploy gồm push nhánh/tag, tạo release, upload bộ cài/SHA256/checkpoint và xác minh tải công khai. Không cài/khởi động bản mới trong thư mục `Highlight destop test`, không đổi lịch thật, không POST/DELETE Facebook, không thêm role/tạo token. Release/tag/bộ cài v1.2.3 đã công bố và tag v1.2.4 local được giữ nguyên.

## Đóng gói

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File build_release.ps1 -Version 1.2.5 -SkipTests -ToolSource 'E:\OPENCLAW\BOB\Highlight destop test\bin' -RuntimeSource 'E:\OPENCLAW\BOB\Highlight destop test\runtime' -IconSource 'E:\OPENCLAW\BOB\Highlight destop test\app.ico' -WhisperModelSource 'E:\OPENCLAW\BOB\Highlight destop test\models\faster-whisper-small'
powershell -NoProfile -ExecutionPolicy Bypass -File checkpoints/tools/v1.2.5/inspect_payload.ps1
```

Không thêm/chạy test chức năng hoặc hồi quy. Rà soát source/cú pháp trước build; công cụ inspect chỉ đọc payload/hash/identity/seed, không chạy app/bộ cài hoặc gửi Meta request. Source sạch và tag local v1.2.5 cố định trước build.

**Build và payload inspection đã hoàn tất.**

- Installer: `release/Highlight_Desktop_Test_Setup_v1.2.5.exe`, **705077760 bytes**.
- SHA256: `8194509413b225e4217231bc9441be406e2f18132c3b1b0f7395c3c3b53f53b0`.
- Source commit/tag v1.2.5: `1bed062ae03f67fbedcfda468cbc818878830ba6`, build identity `source_dirty=false`, app/prerelease v1.2.5, Meta API v24.0.
- Payload khớp **19 file** source; không còn production v22, credential seed rỗng, không có dữ liệu người dùng/lịch/token/machine identity. Evidence: `checkpoints/evidence/v1.2.5/installer_payload.json`.
- AST rà soát cú pháp 10 file Python thay đổi; không execute code app. Không chạy hồi quy/chức năng hoặc POST Meta. Tại mốc inspect bộ cài chưa cài vào runtime thật và chưa publish GitHub; sau đó người dùng đã yêu cầu deploy.
- Bản tiện tải được sao chép ra `E:\OPENCLAW\BOB\Highlight_Desktop_Test_Setup_v1.2.5.exe` cùng SHA256. Hash của bản sao phải khớp installer đã inspect.

Các commit cập nhật checkpoint/evidence sau build có thể nằm sau tag v1.2.5; không đổi tag hoặc code đã đóng gói. Root `CODEX_CHECKPOINT_LATEST.md` trỏ tới checkpoint này.

## Phát hành hoàn tất — 2026-10-06

**Đã công khai GitHub v1.2.5**, Release ID `404429104`, `draft=false`, `prerelease=true`. Xác minh xong lúc `2026-10-06T07:42:54.794420+00:00` (**14:42:54 +07**): tag remote đúng source đóng gói, nhánh release đúng commit đã push, cả 3 asset đã tải toàn bộ không đăng nhập và khớp kích thước/SHA256 local cùng digest GitHub.

- [Trang release](https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.2.5)
- [Bộ cài v1.2.5](https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.2.5/Highlight_Desktop_Test_Setup_v1.2.5.exe)
- [SHA256](https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.2.5/Highlight_Desktop_Test_Setup_v1.2.5.sha256)
- [Checkpoint độc lập kèm docs Meta](https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.2.5/CODEX_CHECKPOINT_v1.2.5.md)

Evidence: `checkpoints/evidence/v1.2.5/release.json`, `deployment_status.json`, `public_download_verify.json`, `prepared_assets.json`, `installer_payload.json`. Nhánh tại mốc công khai là `2a1bb775aa882f9386a4bce262a7f05a7e4d4cc8`; các commit checkpoint/evidence sau đó không đổi source/tag/installer `1bed062ae03f67fbedcfda468cbc818878830ba6`.

Checkpoint asset được viết trước publish và giữ nguyên **25183 bytes**, SHA256 `788ef0330a4ea58e84437fb3a0da2d56349df13a3f7390494e4f1bfcba84374b`. Các bước deploy/resume trong asset là hướng dẫn; trạng thái hoàn tất ở phần này và evidence trên nhánh release. Không thay asset đã công bố bằng bản checkpoint khác.

Offline source bundle: `E:\OPENCLAW\BOB\support\v1.2.5\Highlight_Source_v1.2.5_published.bundle`, gồm nhánh `release/v1.2.5` và tag `v1.2.5`; không chứa installer ignored hoặc runtime private. Session sau đọc checkpoint này/`CODEX_CHECKPOINT_LATEST.md`, clone source nhánh release hoặc bundle vào thư mục mới, kiểm tra build identity thực tế rồi chẩn đoán theo bảng dưới. Bộ cài/checkpoint độc lập cũng có bản tiện dùng ở BOB root.

Phiên phát hành chỉ kiểm tra artifact và tải công khai. **Không chạy test chức năng/hồi quy, không tự cài/nâng cấp runtime hoặc đăng Meta thật**. Runtime v1.2.3 là lần đọc gần nhất trước phát hành; không suy rằng máy người dùng đã chuyển v1.2.5. Sau khi người dùng cài, xác nhận System Info/identity v1.2.5 và Graph v24.0 trước khi phân tích lỗi.

## Tình trạng hạn chế và lịch trễ

Rà soát trước đó thấy 7/41 credential code200 API access blocked ngay cả GET root/Page; header/UA/v24 như MXH cũng lỗi. Chưa có receipt MXH cùng token/Page/thời điểm để kết luận khác biệt POST là nguyên nhân. Thêm personal account vào app role có thể liên quan tới access level, chưa xác minh cấu hình app của từng token lỗi.

**Steering mới nhất trước deploy:** người dùng xác nhận nhóm credential đang dùng để đăng đã hoạt động lại; nhóm credential còn lại trong snapshot không dùng để post và không cần xử lý trong đợt này. Đây là xác nhận của người dùng, không phải kết quả test đăng thật của agent. Không tiếp tục báo snapshot 7/41 cũ là lỗi cần mở khóa toàn bộ. Snapshot GET v24 gần nhất là 13:55:41 +07 ngày 2026-10-06, trước xác nhận này. Cache 300 giây giảm discovery lặp, không được hứa bảo đảm khỏi block.

Lịch trễ trước đó có worker tiến triển nhưng batch pool/đối soát/comment/giãn token 900 giây làm chậm. V24 không có căn cứ để tự giải quyết backlog. Xem các báo cáo ở thư mục BOB: `META_BLOCK_AND_LATE_SCHEDULE_REVIEW.md`, `POST_OPTIMIZATION_REVIEW.md`, `CHECKPOINT_META_POST_TOKEN_COMPARISON_20261006.md`.

## Phát hành và lấy source để session sau sửa tiếp

- Trang release v1.2.5: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.2.5.
- Ba asset cố định: `Highlight_Desktop_Test_Setup_v1.2.5.exe`, `Highlight_Desktop_Test_Setup_v1.2.5.sha256`, `CODEX_CHECKPOINT_v1.2.5.md`. Checkpoint asset là tài liệu độc lập, kèm nguyên văn phần đối chiếu nguồn Meta để không cần các report riêng trên máy tác giả.
- Tag **v1.2.5** luôn là `1bed062ae03f67fbedcfda468cbc818878830ba6`. HEAD nhánh **release/v1.2.5** có thể mới hơn vì checkpoint/evidence/tooling sau build. Không đổi tag hoặc build khác cùng tên/hash rồi thay asset đã công bố.
- Source/checkpoint mới nhất: `git clone --branch release/v1.2.5 https://github.com/minhpark89/Highlight_Video_Studio.git Highlight-v1.2.5-source`. Nếu đã có worktree, kiểm tra git status trước fetch/chuyển nhánh và giữ thay đổi local.
- Tool deploy: `powershell -NoProfile -ExecutionPolicy Bypass -File checkpoints/tools/v1.2.5/deploy_github.ps1`. Dùng credential GitHub đã có trên máy, chỉ trong memory; không in credential. `github_release.py` có inspect/push/draft/resume/upload/publish/verify. Tạo draft, kiểm tra cả 3 asset digest/size/state trước publish; release đã có thì resume đúng nội dung, không tự thay asset khác.
- Tool public download: `python checkpoints/tools/v1.2.5/verify_public_download.py`, tải toàn bộ cả 3 asset không authentication, đối chiếu SHA256/size với local và digest GitHub.
- Evidence sau deploy ở `checkpoints/evidence/v1.2.5/release.json`, `deployment_status.json`, `public_download_verify.json`. Không coi việc tạo draft/upload là phát hành thành công. Chỉ giao link sau khi release public và tải/hash được xác minh.
- Installer ignored ở `release/`; source clone/bundle không chứa installer hoặc dữ liệu người dùng. Offline source bundle: `E:\OPENCLAW\BOB\support\v1.2.5\Highlight_Source_v1.2.5_published.bundle`.

## Nâng cấp và chẩn đoán ở máy người dùng

1. Kiểm tra app đang chạy bằng `/api/system/info`, `build_identity.json`, PID/port và `data/scheduler_heartbeat.json`. Bộ cài đã phát hành không đồng nghĩa runtime đã nâng cấp. Launcher chọn cổng loopback tự do; không cố định 5080 hoặc dùng PID từ snapshot cũ.
2. Trước khi cài, chờ lượt upload đang chạy kết thúc và đóng app cũ. Installer tự dừng instance tại đích, backup state vào `update_backups/<timestamp_guid>` rồi tự mở launcher. Chọn đúng thư mục cài đặt cũ để giữ dữ liệu; không cài nhầm thư mục mới rồi tưởng mất queue. Không ép dừng upload chưa rõ kết quả.
3. State cần bảo toàn: `posts.json`, `tokens_vault.json`, `pages.json`, `page_groups.json`, `token_groups.json`, config, toàn bộ `data/` chứa ledger/content/First Comment và media người dùng. Backup chỉ local/private; không commit/upload raw state/token/config/log.
4. Sau khi người dùng cài, System Info phải báo **app v1.2.5, Graph v24.0**, packaged source commit đúng `1bed062...`. Kiểm tra build identity trước khi quy lỗi mới cho backend v1.2.5.
5. Thu thập lỗi theo **post_id/page_id/token_id nội bộ**, mốc thời gian có timezone, loại App/Meta schedule, status/claim, Website/comment readiness, Meta upload/video/post ID, receipt, HTTP/code/subcode/trace. Không cần raw token hoặc App Secret trong report gửi LLM/GitHub.
6. Log launcher/backend: `server_error.log` tại thư mục cài; chỉ lấy đoạn đã redacted. Heartbeat ở `data/scheduler_heartbeat.json`. `/api/posts/<post_id>/meta-diagnosis` có thể gọi GET Meta để quan sát object hiện hữu; không phải thao tác đăng/xóa.
7. `meta_publish_attempt` mới lưu Init/Finish bị từ chối trên post row. `meta_last_publish_attempt` là receipt đường recovery cũ và hiện được `meta_diagnostics.py`/endpoint dùng. **Hai field chưa hợp nhất trên UI**; session sau phải đọc cả hai để không mất evidence hoặc lầm một GET thành công là đã publish thành công.
8. Khi network/Finish/comment kết quả không rõ, giữ `outcome_unknown`, Meta IDs và receipt; đối soát object cũ trước. Không xóa row/ID/claim để "thử lại" hoặc upload lại video. Comment lỗi không được biến Reel đã xác minh published thành failed rồi repost.

## Bản đồ source theo triệu chứng

| Triệu chứng | Source/evidence cần đọc |
| --- | --- |
| Page token cũ, mapping mất/sai credential, API access blocked | `src/publisher/token_vault.py`: verify_identity/discover_pages/read_permissions/ensure_page_access/pause_page_access; `page_manager.py`: resolve_verified_mapping/sync_pages_from_token; `meta_preflight.py`: resolve_page_token; `docs/META_V24_BACKEND.md` |
| Thiếu CREATE_CONTENT/MODERATE/scope, SYS label bị nhầm loại token | `meta_preflight.py`, `meta_api.py`, metadata Vault; phân biệt task từ Page và permission từ root token; permissions_status unverified không phải scope đã cấp/đã thiếu |
| Lỗi Start/upload/Finish, upload không rõ, published chưa xác minh | `src/publisher/meta_reel_poster.py`; `web/meta_handoff.py`; `web/scheduled_publisher.py`: _publish_claimed_post/_resume_complete_upload; `web/meta_diagnostics.py`; giữ upload ID/receipt |
| First Comment pending/error/verification_pending hoặc comment trùng | `src/publisher/first_comment_queue.py`; `MetaReelPoster.post_first_comment`; scheduled_publisher.prepare_first_comment; task MODERATE/scopes và đúng publication ID; không gửi comment mới khi outcome unknown |
| App giữ lịch quá giờ, worker còn sống nhưng ít bài được cấp lượt | `web/scheduled_publisher.py`: _process_scheduled_posts_once/process_scheduled_posts_once; pool.map chờ cả batch; reconcile/comment/cleanup tuần tự; `multi_pc/publishing_settings.py`; heartbeat, token_gap_seconds, next_retry_at; `POST_OPTIMIZATION_REVIEW.md` local |
| Lên lịch hôm nay/overflow/frozen/claim/revision conflict | `src/output_scheduling.py`, `src/output_pipeline.py`, `web/app.py:api_schedule_today`, `web/static/group_review.js`; bài đã frozen/Meta ID không dùng lịch-hôm-nay để reset |
| Runtime vẫn bản cũ, thiếu module hoặc không mở app | `build_identity.json`, `/api/system/info`, `AppLauncher.cs`, `Installer.cs`, `run_server.py`, requirements lock và `server_error.log`; không sửa scheduler trước khi biết runtime đúng phiên bản |

Các test hiện hữu để tham khảo/khi được yêu cầu kiểm thử: `test_page_token_sync.py`, `test_meta_credential_recovery.py`, `test_meta_native_handoff.py`, `test_meta_queue_handoff.py`, `test_scheduling_publish_flow.py`, `test_first_comment_audit.py`, `test_parallel_publishing.py`, `test_schedule_today.py`, `test_installer_data_preservation.py`, `test_release_guards.py`, `test_github_deploy.py`. **Không test nào trong danh sách này đã được chạy cho v1.2.5**. Kết quả 632 passed của v1.2.3 không được gán cho backend mới.

## Các tối ưu còn lại và thứ tự đề xuất

1. Dispatcher cấp bài mới khi một future hoàn tất; pool lâu dài, giữ lane/token fingerprint/Page lock và claim/lease. Hiện vẫn pool.map chờ cả batch; không tuyên bố v1.2.5 đã sửa backlog.
2. Tách/budget reconcile, First Comment, recovery và cleanup để không giữ luồng dispatch. Lock discovery theo credential vừa thêm chỉ serialize discovery, không phải semaphore toàn giao dịch publish của mọi đường gọi.
3. Hiển thị lý do chờ: token gap, upload đang chạy, cooldown/quota, credential access, Website/comment readiness, thời gian cấp lượt sớm nhất. Đo queue wait/discovery/upload bytes/Finish/readback/ghi JSON rồi chọn mức concurrency.
4. Hẹn lại bài scheduled đã approved/frozen nhưng chưa gửi Meta bằng thao tác có preview và revalidation dưới lock; giữ nội dung/Website/credential/ledger. Không áp dụng cho publishing/processing/meta_scheduled/Meta ID/outcome_unknown.
5. Journal từng giai đoạn và logical_request_id, hợp nhất receipt trên UI; tiếp tục tăng bảo vệ comment unknown. Mã hóa credential cần bao phủ Vault/Page mappings/comment queue/post legacy, không chỉ Vault. Không đổi schema/migrate state live khi chưa có thiết kế có thể review.
6. Quota: docs Reel hiện tại nêu 30 bài API/24 giờ; pacing 900s hiện tại là cấu hình app, không phải quota cố định Meta. Không tăng concurrency/hạ token gap hoặc đổi credential/app để xử lý restriction chỉ dựa vào cảm giác nhanh/chậm.

## Phân biệt tuân thủ Meta và kết quả thực tế

- Hợp lệ về auth/request không chứng minh app đã có App Review/Advanced Access, role hoặc Page asset assignment cần thiết. System User phải được cấp app/tài sản tương ứng. Người dùng ngoài role/business liên quan cần quy trình ủy quyền phù hợp.
- v24 là phiên bản người dùng yêu cầu giống MXH; tài liệu hiện tại có ví dụ v25/v26. Không gọi v24 là Graph mới nhất hiện nay hoặc hứa tự gỡ restriction.
- Nếu app bật Require App Secret, cần server backend tin cậy giữ secret và proxy appsecret_proof; không nhúng App Secret vào installer desktop. Backend này chưa triển khai dịch vụ proxy đó.
- MXH khác rõ nhất ở refresh Page token trước publish, key semaphore và journal; v1.2.5 cập nhật phần refresh/permissions/auth. Chưa benchmark trực tiếp cùng Page/token/media/network; chưa có POST receipt chứng minh MXH giải quyết restriction mà Highlight không giải quyết ở cùng thời điểm.
