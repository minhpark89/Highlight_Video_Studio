# Highlight Desktop Test v1.2.7 — CMS validation and verified video recovery

Ngày 2026-10-06, Asia/Saigon. Nhánh `release/v1.2.7`, Meta Graph **v24.0**. Phiên này tiếp tục hai lỗi mới sau khi người dùng tự cài v1.2.6. Các release/tag/asset cũ giữ nguyên. Trạng thái phát hành cuối xem phần Deployment bên dưới và `checkpoints/evidence/v1.2.7/`.

## Yêu cầu được chốt

- Website đã có bài nhưng app vẫn báo `Public CMS article contains a non-English paragraph`, giữ bài ở preparing.
- Nút Đăng lại MP4 yêu cầu tự nhập tên file; người dùng không biết clip nào hợp lệ.
- Người dùng chọn **ưu tiên video khác trong kho, chuẩn bị Content/Website mới đúng nguồn; nếu kho không phù hợp thì render lại nguồn gốc**.
- LLM vẫn ưu tiên; lỗi/quota có fallback như v1.2.6. Thumbnail ưu tiên model ảnh, ảnh body ngang lấy video dài gốc, mọi Website phải có embed nguồn và First Comment đúng một link Website.
- Đã có quyền phát hành bộ cài và checkpoint. Không tự cài/đóng app thật, thay lịch/token hiện có hoặc gọi publish/delete Meta/CMS thật trong phiên sửa.

## Nguyên nhân CMS và sửa

Runtime người dùng được đọc tại `http://127.0.0.1:64119`: v1.2.6, source tag `15d5157d3ab3bf05ec5c1c6a2c08645d9d9ed643`, Graph v24. Các lần lỗi mới ~16:10–16:14, không chỉ là cờ lỗi cũ. Bốn public URL HTTP200 có đúng nguồn YouTube, 3 ảnh và >600 từ. Langdetect tự tin đọc nhầm heading tiếng Anh thành Indonesian/German/Dutch:

| Content package | Heading bị đọc nhầm | Original video |
|---|---|---|
| content_1791274527_0971f01a | Yamadonga Telugu Full Movie … Full Uncut Breakdown & Scene Analysis | vacL8i-A4tk |
| content_1791274681_0427af31 | Key Elements That Define Ek Ka Dum | 9qoXM6P5u9Y |
| content_1791274714_859f7fcc | Understanding Strategic Vulnerabilities | Uj63XI_d7_A |
| content_1791274719_e4b8c58d | A Moment Frozen in Time | utVvVQF3Qmo |

Private package headings và public headings khác nhau, có thể liên quan propagation/cache CMS nhưng **chưa chứng minh**. Không khẳng định lỗi cache. Có thể tái hiện rõ lỗi nhận diện trên HTML public.

`src/english_text.py`: lexicon CMUdict đóng gói, lazy load có lock, chỉ áp dụng ngoại lệ lexical cho heading h1–h6 và CMS title. Bài hoàn chỉnh vẫn phải qua English gate, từng đoạn p/li vẫn kiểm tra độc lập. Chặn script ngoại và foreign markers. Heading ngắn cần >=3 từ đã biết, >=90% coverage; tiêu đề có tên riêng cần >=6 từ English, >=60% coverage và >=2 thuật ngữ English về video. Không thêm dependency hoặc gọi network để nhận diện ngôn ngữ. Đây không phải bộ dịch; độ chính xác language detection với Latin text quá ngắn vẫn có giới hạn vốn có.

Lexicon 124082 từ, upstream `cmusphinx/cmudict`, pinned commit `74790861f652b15e4ac49015a90074ad62a27690`; SHA256 `89134aa67bb30f22112eca1314260c9da5b80de5c3532b4a1d7347dfd2f00b1e`. Giữ `src/data/CMUDICT_LICENSE.txt` và provenance JSON trong payload.

`retry_package(repair_website=True)` không ép LLM tạo lại nếu private package đã có bài English hợp lệ. `repair_existing_website_article` vẫn đọc CMS authenticated và xác minh public English/quality/embed đúng URL. Bài sai, thiếu từ/ảnh hoặc explicit regenerate vẫn sửa. Bài hợp lệ chỉ xác minh lại, tránh thêm LLM/CMS update. Tuyệt đối không đánh dấu ready chỉ vì URL có HTTP200 hoặc có embed.

## Video recovery: source map và luồng

| File | Thay đổi |
|---|---|
| src/video_recovery_media.py | Kho output, phân trang 12, FFprobe song song 4, cache theo size/mtime, hash/claim/source, safe preview paths, mốc cắt, provenance |
| web/static/video_recovery.js | Cards chọn clip, duration/dimensions/size/source/reason, preview, pagination, render và progress |
| web/video_recovery_tasks.py | Render nền theo yêu cầu, tối đa 2 task, task persisted, interruption/retry, không tự tạo lịch |
| web/video_recovery.py | Bài thay thế preparing, bỏ URL/caption/comment của video khác; giữ audit/Meta ID cũ; deterministic replacement ID |
| web/app.py | recovery-videos / recovery-preview / render-recovery; fresh exact Meta check trước render và trước tạo replacement; enqueue và resume Content |
| src/output_pipeline.py | reserve_recovery chuyển claim unassigned hoặc source của bài lỗi, chống alias hash/claim, durable intent/replay cả khi Daily disabled |
| src/content_packages.py | Chỉ đưa bài phục hồi vào scheduled/meta_handoff sau Website/embed/comment/caption ready; Meta time hết hạn thành safe local retry |
| web/scheduled_publisher.py, web/meta_handoff.py | Kiểm tra SHA256 MP4 được duyệt trước publish, không upload nếu bytes thay đổi |
| web/post_retry.py | recovery_schedule có thể retry qua App, không có remote ID/outcome unknown |

### API và điều kiện

1. `GET /api/posts/<id>/recovery-videos?offset=0`: chỉ đọc kho và claim. Mỗi trang kiểm tra 12 MP4, max 4 FFprobe cùng lúc. Có video/title/duration/size/dimensions/source, nút chọn chỉ bật khi medial valid và source/claim phù hợp. File hỏng/đang render/được giữ/thiếu link nguồn có lý do. Không quét/tạo lịch cho nguồn ngoài output tự ý.
2. `GET /api/posts/<id>/recovery-preview?filename=...`: safe path nằm trong output, FFprobe trước serve, hỗ trợ file dưới `_recovery`.
3. `POST /api/posts/<id>/render-recovery` với `confirm_render=true`, exact `video_id`: đọc mới Meta, bắt buộc terminal failure + upload complete + copyright false + publishing not_started/error/failed/rejected + HTTP200 đúng ID. Render tại `output/_recovery/recovered-<uuid>.mp4`; watcher Daily dùng `glob('*.mp4')` nên không tự intake file này. User xem trước/chọn sau render. Không giữ scheduler lock lúc render. Không tải lại YouTube hoặc post trong worker render.
4. `GET .../render-recovery`: task state/message. Task persisted tại `data/video_recovery_tasks.json`, registry nguồn/hashes tại `data/video_recovery_sources.json`. Nếu app đóng giữa chừng, báo interrupted và cho render mới. Bytes biến đổi bị từ chối.
5. `POST .../replace-failed-video`: confirm/exact video ID, cycle lock + pipeline lock + posts lock. Meta check mới. Clip check/hash mới, claim nguyên tử, original superseded giữ IDs, replacement preparing. Backend luôn chuẩn bị Content theo source được xác minh; client không thể yêu cầu reuse caption/URL của video khác. Bấm lặp trả replacement hiện có. `ensure_content_package` có thể reuse package đúng nguồn/bytes, nhưng URL existing phải được revalidate khi item ready.
6. Khi đổi clip nguồn khác: Website URL/comment/caption cũ được xóa khỏi replacement, original vẫn giữ lịch sử. Khi render đúng nguồn của bài cũ và source match được xác minh, có thể giữ URL cũ rồi revalidate CMS tại URL đó. Cả hai trường hợp LLM auto ưu tiên với fallback.
7. Content complete: phải ready Website + embed + youtube_embed_verified + English social text + comment có đúng một URL. Chỉ khi đó freeze nội dung và cho scheduler upload. Meta giờ quá gần/qua thành failed local `recovery_schedule`, có nút Đăng lại bằng App; không gửi upload/outcome unknown.

### Claim/restart protections

SQLite là durable source claim. Không lấy source đã assigned cho bài khác/published. Stock chưa Page đang preparing/draft có thể chuyển cho replacement; stock row thành superseded. Kiểm tra cả alias cùng bytes, kể cả legacy row chưa lưu hash. Không bỏ source cũ của bài lỗi ra kho để tự repost. `restore_recovery_intents` phục hồi crash giữa commit claim và save posts, rồi `_resume_recovery_content` gắn Content nếu request bị gián đoạn trước enqueue. Source đã committed không được claim hai lần.

File hỏng ban đầu vượt EOF: mốc render lấy duration thật. Mốc còn hợp lệ được giữ/clamp, mốc vượt nguồn được chọn lại trong nguồn dựa clip index (tối đa 60 giây) và hiển thị rõ để xem trước. `subtitle_style='none'` tránh gọi model phụ đề trong recovery; source caption có sẵn vẫn nằm trên hình gốc. Tên nguồn hoặc đường dẫn gốc thiếu/mất: task báo lỗi và yêu cầu chọn kho hoặc tải lại nguồn, không tải tự động trong bản này.

## Kiểm tra và giới hạn

- Targeted offline suite, tất cả HTTP thật bị chặn bởi tests/conftest.py. Evidence: offline_tests.json/txt. Lượt cuối **537 passed, 4 skipped, 29 subtests passed**, gồm test renderer thực dùng FFmpeg; kết quả sẽ được cập nhật nếu source thay đổi.
- Chromium interaction: 5 checks, 0 JavaScript error; mọi request bị intercept. Kho hợp lệ/invalid/reserved, preview, pagination, progress, render không tự chọn/lên lịch. `browser_ui.json`, `recovery_picker.png`. Fixture UI, không phải ảnh runtime người dùng.
- Replay 4 HTML public snapshot sau cài v126: English validation passed, original embeds đúng; `public_cms_replay.json`. HTML cache ở temp ignored, không commit raw private state.
- Kiểm tra path escape, changed file, duplicate click/hash, claim recovery/crash, foreign paragraphs/headings, incomplete Content/embed, expired Meta schedule, rejection evidence. Actual FFmpeg render từ fixture, không render job thật.
- Chưa thực hiện live CMS update/Meta publish/cancel/delete, không thay app/lịch/token đang dùng. Offline success không chứng minh Meta sẽ chấp nhận mọi video/token.

## Build / phát hành

Tools tại `checkpoints/tools/v1.2.7/`: verify_offline.py, offline_ui.py, inspect_payload.ps1, prepare_assets.py, github_release.py, github_deploy.py, verify_public_download.py. Quy trình: commit source sạch + annotated immutable tag v1.2.7 → build với source identity → inspect installer/payload/31 file/empty secrets → prepare assets → inspect/push/draft/upload/publish/verify → tải đầy đủ anonymous và hash → commit checkpoint/evidence cuối trên branch. Không retag hoặc đổi asset đã public.

Build bằng PowerShell, input chỉ đọc từ runtime thật:

```powershell
$env:PATH = 'E:\OPENCLAW\BOB\Highlight destop test\bin;' + $env:PATH
python checkpoints/tools/v1.2.7/verify_offline.py 'E:\OPENCLAW\BOB\Highlight destop test\bin\node.exe'
python checkpoints/tools/v1.2.7/offline_ui.py
powershell -NoProfile -ExecutionPolicy Bypass -File build_release.ps1 -Version 1.2.7 -SkipTests -ToolSource 'E:\OPENCLAW\BOB\Highlight destop test\bin' -RuntimeSource 'E:\OPENCLAW\BOB\Highlight destop test\runtime' -IconSource 'E:\OPENCLAW\BOB\Highlight destop test\app.ico' -WhisperModelSource 'E:\OPENCLAW\BOB\Highlight destop test\models\faster-whisper-small'
```

### Deployment

Build và inspect hoàn tất: tag/source `06ad9f5328e16f3b5794ae8478adfe753a5f7ca3`, clean identity, Graph v24.0, 31 source/lexicon/license files khớp; không có state/credential thật. Installer `Highlight_Desktop_Test_Setup_v1.2.7.exe`, **705445376 bytes**, SHA256 `95ad9365a65eaa88fdad20b83034a2d90c0733edaf2efeda2ea0d1480f55170d`. Offline cuối **537 passed, 4 skipped, 29 subtests passed**; JS 4 inline + 3 external, templates identical; Chromium 5 checks/0 errors.

**Đã public và xác minh tải đầy đủ ba asset**. Release ID `404556122`, draft=false/prerelease=true. Release: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.2.7. Anonymous GET HTTP200/size/SHA256 khớp toàn bộ installer, checksum và checkpoint lúc **2026-10-06 17:14:21 +07**. Evidence `release.json`, `deployment_status.json`, `public_download_verify.json`. Installer public SHA256 khớp build đã kiểm tra ở trên.

Asset checkpoint được chuẩn bị trước public và giữ nguyên sau upload; thông tin cuối ở nhánh release và checkpoint này. Tag source cố định; nhánh checkpoint/evidence có commit mới hơn. Source backup offline: `E:\OPENCLAW\BOB\support\v1.2.7\Highlight_Source_v1.2.7_published.bundle`. Không cài vào app thật, không thay live posts/token/schedules, không gửi publish/delete Meta/CMS.

## Session sau

1. Đọc checkpoint này, latest, META_V24_BACKEND.md và evidence v127. Kiểm tra identity/port app thật trước mọi thao tác. Checkpoint v126 mô tả nền Content/image/comment; v125 mô tả Meta token binding/cache.
2. User tự đóng app/cài installer vào đúng thư mục đang dùng. Không tự dừng/cài runtime nếu chưa có yêu cầu. Không xóa posts/token/ledger/Meta IDs/comment receipts.
3. Với lỗi Public CMS: Thử lại Website đúng bài/URL; bộ kiểm tra mới revalidate trước regenerate. Với MP4 rejected: Kiểm tra Meta → Đăng lại MP4 → chọn clip dùng được + xem trước → tạo lịch. Nếu kho không phù hợp, Render lại từ gốc, xem trước/chọn output rồi tạo replacement. App giữ failed IDs/audit; tránh tự upload lại ID unknown/scheduled/published.
4. Thu lỗi có app version/source, post/package ID, media filename/hash, retry_stage, schedule, source embed ID và sanitized Meta observation. Không đưa token/password/API key vào log/checkpoint. Nếu Meta restricted, xử lý exact credential/Page, không coi nâng Graph v24 hoặc cache300s bảo đảm hết block.
5. Offline reproduction: fixtures dưới tests, mocks HTTP, tests/test_v127_media_and_cms.py. Có thể đọc state thật nhưng sửa/test trên bản sao riêng. Runtime thật trong phiên này giữ nguyên.
