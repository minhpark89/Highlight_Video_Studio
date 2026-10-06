# Checkpoint v1.2.6 — Content fallback và phục hồi video lỗi

Ngày 2026-10-06, Asia/Saigon. Source: `E:\OPENCLAW\BOB\source-worktree`, nhánh `release/v1.2.6`, kế thừa HEAD v1.2.5 `e57be25f5f47d91bc64162fba750e3fdc63d0697`. Runtime người dùng: `E:\OPENCLAW\BOB\Highlight destop test`. Hai thư mục độc lập.

## Yêu cầu đã chốt

- Các bài processing cũ không có nút xóa, nhiều bài từ ngày 4 chưa đăng; cần phục hồi và tránh đăng trùng.
- Nhiều bài chuẩn bị Content/Website lỗi; thử lại phải có hiệu lực. LLM được ưu tiên; lỗi, quota hoặc JSON không hợp lệ phải dùng fallback.
- Thumbnail đầu bài ưu tiên model ảnh. Chỉ dùng frame từ video dài gốc khi model ảnh không trả ảnh hợp lệ, lỗi hoặc hết quota; lựa chọn frame-only trong cấu hình vẫn được giữ.
- Hai ảnh minh họa luôn cắt từ video dài gốc, xuất ảnh ngang; không lấy Reel dọc làm nguồn.
- Nội dung fallback dựa vào tiêu đề, mô tả, transcript nguồn; giữ form bài English, ít nhất 600 từ, một câu mỗi đoạn, heading, phần tóm tắt và video cuối bài. Không bịa diễn biến/kết quả khi nguồn thiếu thông tin.
- Bài Website chứa iframe YouTube gốc (hoặc HTML5 video dài gốc đã có public URL được xác minh nếu không có YouTube). First Comment chứa đúng URL Website đã xác minh một lần.
- Người dùng đã yêu cầu phát hành bản mới lên GitHub để tự tải/cài, kèm checkpoint. Không hỏi lại quyền phát hành. Không thay runtime thật, lịch thật, token hoặc role Meta trong lượt này.

## Phát hiện từ runtime v1.2.5 — chỉ đọc, số liệu lịch sử

Identity runtime xác nhận v1.2.5 / Graph v24.0. Snapshot 1367 package ready, 123 failed; app chạy đồng thời nên số lượng có thể thay đổi.

- 9 lỗi article paragraph non-English, 10 lỗi public paragraph non-English, 34 lỗi public article English, 35 HTTP429, 30 thiếu ảnh nguồn, 5 thiếu video gốc/public video.
- Heading English `A Lesson in Cabin Etiquette` bị nhận sai là ngoại ngữ.
- Video gốc của nhóm lỗi ảnh là 1440×1080 (4:3), bị bộ lọc cũ loại vì tỷ lệ dưới 1.45. Nguồn `job_1790748353_62156a.mp4` dài 726.714921s và `job_1790748353_005f52.mp4` dài 614.794739s.
- Bốn bài có quan sát terminal: uploading complete, video_status error, publishing not_started, copyright false:

| Post local | Meta upload video ID |
| --- | --- |
| post_1791183231_2ded99 | 1642552567376649 |
| post_1791183231_19d128 | 2285116458712741 |
| post_1791183243_6ef718 | 3049285172077305 |
| post_1791183244_b98215 | 1456548559709071 |

Đây là bằng chứng lịch sử, không phải quyền xóa/đăng lại từ cache. Endpoint luôn đọc lại trạng thái Meta trước khi chấp nhận thao tác.

Những bài khác có 368/4854002 yêu cầu xác minh danh tính; một số vẫn publishing scheduled. Không xóa/upload lại khi chưa có bằng chứng lỗi terminal mới. Chuyển Graph v24 hay cache 5 phút không được coi là cách mở khóa ứng dụng/tài khoản.

## Thay đổi backend

### Content và First Comment

`src/content_packages.py`: cả auto và llm đều ưu tiên LLM, fallback khi provider lỗi, JSON lỗi, quota, circuit mở hoặc HTML sau normalize không đạt English. Fallback tự kiểm tra English; chỉ giữ phần thông tin nguồn có thể sử dụng. Template comment được kiểm tra ngôn ngữ/link; lỗi template hoặc ghi rotation dùng mẫu built-in. Source/reason được ghi lại để session sau phân biệt lỗi LLM và lỗi Website.

`src/english_text.py`: sửa nhận diện heading English ngắn; vẫn chặn paragraph ngoại ngữ và mixed content. Không hạ yêu cầu bài public English.

`web/app.py` lưu `source_transcript_excerpt` vào job khi đã lấy transcript YouTube/Whisper. `website_publisher.get_clip_metadata` đọc trường này. Excerpt giới hạn 1800 ký tự từ mở/giữa/cuối; không lưu toàn transcript lớn vào jobs.json. Fallback nguồn ưu tiên mô tả, excerpt đã lưu, ASS clip cũ, rồi thử lấy transcript YouTube với timeout kết nối/đọc 5/15s. ASS được ghi rõ là các câu trong clip, không giả làm transcript toàn video.

Không có transcript/mô tả: bài là hướng dẫn xem nguồn theo tiêu đề, không tự viết tin về các sự kiện không được cung cấp. Nguồn ngoại ngữ không thể tự dịch chính xác sang English nếu hoàn toàn không có dịch vụ ngôn ngữ; fallback bỏ phần không thể xác minh ngôn ngữ và giữ video nhúng để người đọc xem nguồn.

### Ảnh và form Website

`src/publisher/website_publisher.py` chấp nhận nguồn width>height gồm 4:3, chọn frame rồi crop ngang 16:9. Cả đường OpenCV và ffmpeg đều kiểm tra nguồn ngang. FFmpeg chạy ẩn trên Windows. Đường không có OpenCV vẫn lấy được duration bằng ffprobe khi metadata thiếu mốc clip.

Model ảnh độc lập với mode text no_llm. Hai ảnh body từ nguồn dài; nếu thumbnail model thất bại cần frame thứ ba. Bài có ba URL ảnh riêng, ghi image_source/model/fallback_reason. Nếu không còn video dài local hoặc upload CDN/CMS lỗi thì báo đúng lỗi tài nguyên, không dùng ảnh Reel dọc thay nguồn.

Sửa Website giữ URL/slug/CMS ID/version và kiểm tra concurrent edit. Bố cục dùng renderer chuẩn: hero đầu, summary, body illustrations xen nội dung, Full Uncut Footage và player cuối. Giữ các media URL đã có; có thể thêm ảnh nguồn thiếu sau khi upload và cập nhật thumbnail/og_image, không được loại bỏ ảnh/player cũ. Bài English hợp lệ, đủ từ được revalidate; bài ngắn/non-English hoặc được yêu cầu regenerate được viết lại.

`core/website_article_service.py`: kiểm tra ba ảnh URL khác nhau trong article, không tính ảnh sidebar/footer; kiểm tra iframe HTTPS đúng host và đúng original video ID hoặc source trong video tag. URL plain text không được coi là embed.

### Retry Website

Nút thử lại relink post vào package, xóa error/backoff cũ và yêu cầu text mới. Package đang queued/running được giữ và relink, không mở worker trùng. Existing article sửa tại cùng URL; không tạo bài CMS khác. URL được lưu trước readback, kể cả reuse stable slug.

CMS429 có tối đa 5 lần retry trễ, delay 60/120/240/480/960s, giới hạn exponential 1800s; numeric Retry-After được tôn trọng tới 3600s. LLM circuit không chặn Website retry. Sau giới hạn vẫn báo lỗi để người dùng xử lý; không hứa thành công khi CMS/source không sẵn sàng.

### Video Meta processing lỗi

`web/scheduled_publisher.py`: sau fresh GET, nếu có bằng chứng lỗi terminal chặt chẽ thì chuyển processing thành failed/rejected, giữ upload ID và kết thúc vòng processing; không tự upload lại.

`web/video_recovery.py`: replacement qua Meta giữ lịch hoặc App đăng ngay. MP4 phải qua ffprobe; Website/comment phải ready, comment đúng một URL. Giữ bài gốc superseded, Meta ID cũ, URL/comment; ID replacement ổn định và chống tạo hàng đợi trùng.

`web/app.py` DELETE chỉ xóa local row khi fresh observation xác nhận terminal error, upload complete, publishing not_started/error/failed/rejected, copyright=false, đúng upload ID, không có published ID/cancel/replacement. Audit không chứa secret ở `data/meta_failed_removed.json`. Không DELETE Meta hoặc xóa file MP4. Với bài scheduled/published/unknown, giữ hàng rào phục hồi hiện có.

UI mở nút Đăng lại MP4 và thùng rác cho bài lỗi được xác nhận; endpoint vẫn kiểm tra mới. Chẩn đoán lấy receipt Finish mới nhất giữa hai trường lịch sử. Lỗi identity yêu cầu xử lý quyền/danh tính thật trên Facebook trước khi phục hồi video hiện có.

## Kiểm tra trước build

Người dùng yêu cầu kiểm tra và đảm bảo Content/fallback. Chỉ chạy kiểm tra offline có mock; fixture chặn HTTP thật và background worker. Không ghi Meta/CMS/runtime người dùng.

Lượt kết hợp 29 module sau sửa: **434 passed, 4 skipped, 29 subtests passed**. Skip liên quan OpenCV/môi trường; đường ffmpeg dùng video synthetic 4:3 đã chạy thành công. Các test cũ được cập nhật theo contract v1.2.5/v24: PROFILE_PLUS_MANAGE không đủ đăng, alias CREATE_CONTENT hợp lệ, MODERATE riêng cho comment, upload chỉ rupload.facebook.com, refresh discovery có mock và poster nhận page_id của comment.

Lượt cuối có thêm Page/token sync và parallel publishing, cùng syntax JavaScript, được ghi tại `checkpoints/evidence/v1.2.6/offline_tests.json`, `offline_tests.txt`, `javascript_syntax.json`. Không suy diễn syntax check là browser interaction test hay offline test là bài Facebook thật.

```powershell
$env:PATH = 'E:\OPENCLAW\BOB\Highlight destop test\bin;' + $env:PATH
python checkpoints/tools/v1.2.6/verify_offline.py 'E:\OPENCLAW\BOB\Highlight destop test\bin\node.exe'
```

## Build và phát hành

APP_VERSION/launcher/installer/default build chuyển 1.2.6; Meta API giữ v24.0. Commit sạch và annotated tag `v1.2.6` cố định trước build. Không di chuyển tag v1.2.5 hoặc thay asset đã công bố.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File build_release.ps1 -Version 1.2.6 -SkipTests -ToolSource 'E:\OPENCLAW\BOB\Highlight destop test\bin' -RuntimeSource 'E:\OPENCLAW\BOB\Highlight destop test\runtime' -IconSource 'E:\OPENCLAW\BOB\Highlight destop test\app.ico' -WhisperModelSource 'E:\OPENCLAW\BOB\Highlight destop test\models\faster-whisper-small'
powershell -NoProfile -ExecutionPolicy Bypass -File checkpoints/tools/v1.2.6/inspect_payload.ps1
python checkpoints/tools/v1.2.6/prepare_assets.py
python checkpoints/tools/v1.2.6/github_release.py deploy
python checkpoints/tools/v1.2.6/verify_public_download.py
```

SkipTests ở build vì đã chạy lượt kiểm tra riêng với evidence. Inspect đọc payload/identity/hash/seed, không chạy app/installer. GitHub credential từ file local chỉ đọc trong memory; không print hoặc commit. Ba asset: installer, SHA256, checkpoint độc lập kèm tài liệu Meta. Chỉ public sau khi upload/hash đủ; tải công khai toàn bộ để xác minh. Evidence/source docs có thể commit sau tag mà không đổi code đã đóng gói.

Ở mốc viết checkpoint ban đầu, build/publish v1.2.6 **chưa hoàn tất**. Đọc mục bổ sung cuối file và evidence để biết trạng thái thực tế; không coi lệnh trên là đã chạy thành công.

## Session sau: phục hồi đúng bài

1. Đọc checkpoint/latest, identity/PID/port runtime thực tế. Xác nhận v1.2.6/v24.0. Sao lưu private state trước mọi can thiệp live; không đưa token/private state vào checkpoint.
2. Với Website: dùng Thử lại Website, theo dõi package_id/post_ids/stage/source/fallback_reason. URL có sẵn phải được sửa tại URL đó. Chỉ ready sau English/600 words/3 ảnh/embed/readback; First Comment phải chứa đúng URL một lần.
3. Với processing cũ: Kiểm tra Meta đọc đúng upload ID và đúng mapping root token/Page. Chỉ lỗi terminal mới dùng Đăng lại MP4 hoặc thùng rác local. Kiểm tra MP4, đặc biệt timestamp vượt EOF của Bodycam; không đăng lại clip hỏng 262 bytes.
4. 368/4854002: giữ ID, xử lý danh tính/quyền Page rồi đồng bộ và phục hồi video hiện có. scheduled/published/unknown không được upload lại chỉ vì quá giờ.
5. Khi chẩn đoán fallback: phân biệt provider text, model ảnh, nguồn video local và CMS429. LLM fallback không sửa được thiếu tài nguyên hay khóa Meta.

Không cài mới/khởi động app mới hoặc sửa lịch thật trong session phát hành này. Người dùng tự đóng app cũ và cài bản mới cùng thư mục; installer có kiểm tra bảo toàn dữ liệu, không dùng thư mục source làm runtime.

## Tài liệu liên quan

- `docs/META_V24_BACKEND.md`: nguồn chính thức Meta và contract v24 đã triển khai ở v1.2.5.
- `CHECKPOINT_V1_2_5_META_BACKEND_20261006.md`: release trước, 705077760 bytes, SHA256 `8194509413b225e4217231bc9441be406e2f18132c3b1b0f7395c3c3b53f53b0`; giữ nguyên.
- `CHECKPOINT_V1_2_2_META_RECOVERY_20261006.md`, `CHECKPOINT_V1_2_0_20261005.md`: media 262 bytes, giữ Meta ID, bảo toàn comment/ledger và source recovery trước đây.

## Build/payload đã hoàn tất

- Tag/source đóng gói: `15d5157d3ab3bf05ec5c1c6a2c08645d9d9ed643`, `source_dirty=false`.
- Installer `Highlight_Desktop_Test_Setup_v1.2.6.exe`: **705081856 bytes**, SHA256 `d9720eca0e476a3ee0c160b1d1f3a8fef96445bd8d74c0ef3b494e2cba61df8d`.
- Identity: app/prerelease 1.2.6, Graph v24.0, desktop-test, loopback/port riêng; payload 24 file khớp source, không có dữ liệu runtime/machine identity/credential, không còn production v22.
- Kiểm tra cuối: **507 passed, 4 skipped, 29 subtests passed** trong 31 module; HTTP thật bị chặn. Bốn inline scripts và `web/full_script.js` qua Node syntax check, hai templates giống nhau. AST tất cả file production Python trong src/core/web hợp lệ, `git diff --check` không lỗi. Không thử tương tác browser hay cài/khởi động vào runtime thật.
- Evidence: `installer_payload.json`, `offline_tests.json`, `offline_tests.txt`, `javascript_syntax.json` trong `checkpoints/evidence/v1.2.6/`.
- Tool GitHub được bổ sung streaming progress/sanitized upload errors sau tag; tool này không nằm trong payload app. Các commit checkpoint/evidence/tool sau build không đổi source app đã đóng gói hoặc tag.

Ở mốc này, **GitHub v1.2.6 chưa public**. Đọc evidence/publication bổ sung sau khi deploy; asset checkpoint được chuẩn bị trước public và giữ nguyên sau upload.

## Phát hành hoàn tất — 2026-10-06

**v1.2.6 đã public trên GitHub**, Release ID `404495170`, `draft=false`, `prerelease=true`. Tải lại toàn bộ ba asset không đăng nhập hoàn tất lúc `2026-10-06T08:59:43.057850+00:00` (**15:59:43 +07**); HTTP200, kích thước/SHA256 khớp local và digest GitHub.

- [Release](https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.2.6)
- [Installer](https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.2.6/Highlight_Desktop_Test_Setup_v1.2.6.exe)
- [SHA256](https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.2.6/Highlight_Desktop_Test_Setup_v1.2.6.sha256)
- [Checkpoint độc lập kèm docs Meta](https://github.com/minhpark89/Highlight_Video_Studio/releases/download/v1.2.6/CODEX_CHECKPOINT_v1.2.6.md)

Remote tag khớp source đóng gói `15d5157d3ab3bf05ec5c1c6a2c08645d9d9ed643`. Nhánh tại mốc publish là `89ff03a22a261c39a2e94853b73bdf3074f312a1`; commit checkpoint/evidence sau này không thay tag hoặc installer.

Checkpoint asset giữ nguyên **25865 bytes**, SHA256 `1f7b1ee9fd284f6c5c9680862ea05a19efd0b59e1aaf8a7ff888cc4c69f480a9`. Các ghi chú chưa public trong asset là trạng thái lúc chuẩn bị; trạng thái hoàn tất được ghi ở mục này và evidence trên nhánh release. Không thay asset đã công bố.

Evidence cuối: `checkpoints/evidence/v1.2.6/release.json`, `deployment_status.json`, `public_download_verify.json`, `prepared_assets.json`, `installer_payload.json`, `offline_tests.json` và `javascript_syntax.json`.

Bản installer local và SHA256 được đặt thêm ở `E:\OPENCLAW\BOB\Highlight_Desktop_Test_Setup_v1.2.6.exe` / `.sha256`; khớp bytes release. Root latest và checkpoint chi tiết được cập nhật. Bundle source offline: `E:\OPENCLAW\BOB\support\v1.2.6\Highlight_Source_v1.2.6_published.bundle` (nhánh release/v1.2.6 và tag v1.2.6, không chứa runtime private/installer ignored). Xem `source_bundle.json` để xác nhận ref/hash/verify thực tế.

Session sau dùng source mới hoặc clone bundle, đọc identity app đang chạy rồi kiểm tra lại các ID ở bảng lịch sử. **Chưa cài v1.2.6 vào runtime người dùng, chưa sửa lịch thật và chưa POST/DELETE Meta/CMS thật.** Người dùng tự cài rồi dùng Thử lại Website / Kiểm tra Meta theo từng bài.
