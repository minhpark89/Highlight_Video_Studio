# Highlight Desktop Test v1.2.8 — Group slots and faster local views

Ngày 2026-10-06, Asia/Saigon. Nhánh `release/v1.2.8`, Graph **v24.0**. Bắt đầu từ commit documentation v127 `1731ce4a047cb8226b92f19878c60ee9cfa42302`. Tag/bộ cài v127 giữ nguyên.

## Yêu cầu và bằng chứng

Người dùng sửa nhóm NEW thành ba giờ nhưng cửa sổ Lên lịch vẫn chỉ có hai bài/Page. Đọc JSON local cho thấy group times `10:50,15:00,04:00`, trong khi Daily plan group còn `04:00,10:50` và `posts_per_day=2`, scope 100 Pages. Không sửa state đang dùng. `loadGroupDailyModalPlan` ưu tiên `plan.slots`, ghi đè options từ group vừa sửa. `api_save_group` trước đây không đồng bộ Daily plan.

Load nhóm trước đây chờ đồng thời `/api/groups` và `/api/clips`; `/api/clips` đọc jobs, quét output, sort/stat và trả mọi clip, dù bảng nhóm chỉ cần số lượng. Đếm toàn kho còn bị dùng chung cho mọi folder binding. Load bài phân trang trước enrichment đã có từ bản trước, nhưng vẫn parse cả queue và tạo hai writable deep-copy baselines; token audit quét/annotate mọi bài; handoff đọc English trước cả status guard. Filter/page đổi trong khi fetch đang chạy bị bỏ qua bởi `postsTableLoading`.

## Thay đổi

| Source | Hành vi |
|---|---|
| src/output_pipeline.py | `normalize_daily_slots`, lưu `group_schedule_times` riêng với slots đang dùng; `sync_group_daily_plan` cập nhật phân bổ tương lai cho đúng `group:<id>` khi chỉnh giờ/giãn cách |
| web/app.py | Validate giờ trước lưu nhóm; trả `daily_plan`; endpoint đếm theo folder binding; view read-only cho list/detail/audit/summary/health/Page counters; alerts nhẹ |
| web/index.html và web/templates/index.html | Đủ mọi giờ nhóm, default ba khi legacy plan khác cấu hình; giữ giới hạn đã chọn khi snapshot config khớp; cache group cập nhật ngay sau Save; render nhóm trước số video; abort/generation tránh phản hồi cũ |
| web/posts_store.py | `posts_snapshot`: cache revision file, không TTL, không baseline/writer lock trên healthy read; recovery/fail-closed như cũ |
| web/token_audit.py | Index bài/Page/group một lần, stats toàn queue nhưng annotate chỉ selected row copies |
| web/meta_handoff.py | Status/mode/remote-ID guards trước English; mọi kiểm tra English, CMS/comment, path/digest vẫn giữ trước handoff/upload |
| tests/test_v128_group_slots_loading.py | Slots/edit/cap/legacy, view isolation, atomic replace/concurrency/backup, no credentials, folder count, no remote write |

### Lịch và giới hạn

- Options hiển thị đủ distinct HH:MM của group, normalize/sort giống backend, không giới hạn sáu lựa chọn. Chọn 3 gửi cả ba giờ và `posts_per_page=3`. Chọn ít hơn dùng những giờ đầu đã hiển thị trong option.
- `group_schedule_times` là snapshot cấu hình khi lưu plan, **không** dùng để tự phát thêm bài. Worker vẫn chỉ chạy `plan.slots` đã được cắt theo `posts_per_day` lúc lưu. Không đổi thuật toán pacing và source/slot claims.
- Khi sửa group, plan dùng đủ số giờ cũ tiếp tục dùng đủ số giờ mới; giới hạn thấp hơn vẫn giữ (clamp nếu bỏ giờ). Giữ enabled/daily/approval/publish/token scope; không tự bật Daily. Chỉ cập nhật plan đúng một group và không có explicit Pages. Không thay global/multi-group plan.
- Chỉnh tên/folder mà giờ/giãn cách không đổi không thay Daily custom times. Không sửa hàng đợi hoặc slot đã assigned, không thay lịch đã gửi Meta.
- Legacy plan trước v128 không có snapshot; không thể suy ra chắc chắn giới hạn 2 là chủ ý hay stale. Khi config khác slots cũ, **modal mặc định dùng đủ giờ group**. Chỉ xác nhận Lên lịch mới ghi lựa chọn; nâng cấp/GET không tự sửa live plan. Đây là cách xử lý trường hợp NEW đã sửa trước khi cài.

### View cache

- Revision `(dev, inode, size, mtime_ns, ctime_ns)`, stat mỗi request, kiểm tra trước/sau read + sau close. Atomic replacement hoặc sửa file làm revision đổi ngay. LRU tối đa bốn queue paths. Không cache 5 phút, không freeze status/time.
- Shared rows là borrowed read-only; list/detail deepcopy selected rows trước enrichment. Audit endpoint `annotate_posts=[]`. Writable load/save, merge baseline, freeze protections, archive/backup nguyên v127.
- Reader có lock riêng, không đợi writer trên healthy read. Missing/malformed/corrupt primary dùng loader cũ để backup recovery hoặc raise `PostsStoreError`; không đổi lỗi thành queue rỗng.
- Alerts chỉ id/status/stage/sanitized error, tối đa 100; chỉ poll khi Posts active. Health đầy đủ tối đa mỗi 60 giây trên UI. Scheduler health và list refresh chạy độc lập. Không tăng Meta Sync/Graph requests.
- Số video là **số MP4 trong thư mục**, không khẳng định đã FFprobe/hash/claim kiểm tra. Count quét nonrecursive mỗi folder một lần và không đọc jobs/content. Media/source/claim verification vẫn diễn ra khi phân bổ/recovery. Lỗi count không chặn nút/sửa nhóm.

## Kiểm tra offline

Evidence chính: `checkpoints/evidence/v1.2.8/`; tools: `checkpoints/tools/v1.2.8/`.

- Targeted suite gồm các luồng Content/CMS/fallback/Meta/Daily/claims/installer của v127 và test v128. Kết quả cuối: **557 passed, 4 skipped, 29 subtests passed** (17,10 giây). HTTP không mock bị chặn bởi conftest; worker nền bị ngăn khởi động, dữ liệu tạm.
- Chromium `scheduling_ui.py` dùng hàm thật trích từ shipped index; 7 tình huống, 0 JS errors: render nhóm trước inventory, cập nhật count, legacy 2→3, payload ba giờ và giãn cách, explicit cap + >6 giờ, filter race/abort/stale page counter, dedup quiet.
- Syntax 4 inline scripts, 3 external scripts; hai template byte-identical. V127 recovery vẫn có test suite kế thừa; không thay media code.
- Benchmark copy **ẩn toàn bộ credential/tên/ID/content riêng** từ local queue vào temporary folder: 1.431 bài, 31 token, 100 Pages, 50 selected rows; live file ~4,82 MB, bản ẩn ~3,98 MB. So cùng immutable code v127 với code v128, 7 warm requests mỗi bên: list response median **220,78 → 11,68 ms**, ~18,9 lần; v128 first request **32,77 ms**. Queue read median **216,01 → 0,12 ms**. Không đo tốc độ paint/network/media thật. Không hứa mọi máy sẽ có hệ số này.

## Kế thừa v127 / yêu cầu lâu dài

Đọc `CHECKPOINT_V1_2_7_MEDIA_CMS_RECOVERY_20261006.md` và `docs/META_V24_BACKEND.md`. Giữ English CMS validation, retry revalidation, LLM ưu tiên/fallback, thumbnail model ưu tiên, ảnh body ngang từ video dài, embed gốc trong Website và First Comment đúng một link. Video recovery ưu tiên clip kho được kiểm tra, fallback render gốc; phải fresh exact terminal Meta evidence, source matched Content/Website/comment, durable claims và digest trước upload. Không xóa remote ID/outcome unknown để upload lại.

## Build / deploy / tiếp tục phiên sau

Có quyền phát hành bộ cài từ các turn trước. Không tự đóng/cài app thật, thay lịch/token/state đang dùng hoặc gọi publish/delete Meta/CMS thật.

```powershell
$env:PATH = 'E:\OPENCLAW\BOB\Highlight destop test\bin;' + $env:PATH
python checkpoints/tools/v1.2.8/scheduling_ui.py
python checkpoints/tools/v1.2.8/verify_offline.py
$env:PYTHONPATH = (Get-Location).Path
python checkpoints/tools/v1.2.8/benchmark_views.py
powershell -NoProfile -ExecutionPolicy Bypass -File build_release.ps1 -Version 1.2.8 -SkipTests -ToolSource 'E:\OPENCLAW\BOB\Highlight destop test\bin' -RuntimeSource 'E:\OPENCLAW\BOB\Highlight destop test\runtime' -IconSource 'E:\OPENCLAW\BOB\Highlight destop test\app.ico' -WhisperModelSource 'E:\OPENCLAW\BOB\Highlight destop test\models\faster-whisper-small'
powershell -NoProfile -ExecutionPolicy Bypass -File checkpoints/tools/v1.2.8/inspect_payload.ps1
python checkpoints/tools/v1.2.8/prepare_assets.py
python checkpoints/tools/v1.2.8/github_release.py deploy
python checkpoints/tools/v1.2.8/verify_public_download.py
```

Commit sạch/tag trước build; tooling inspection đối chiếu source/tag/Graph/empty secrets. Bump `web/app.py`, `AppLauncher.cs`, `Installer.cs`, `build_release.ps1`. GitHub helper đọc credential file trong bộ nhớ, không in hoặc commit. Deploy có resume/digest guards, không thay public asset. Sau publish phải anonymous download toàn bộ ba asset/hash, commit trạng thái cuối và push branch; giữ tag source/binary immutable. Source bundle dự kiến `E:\OPENCLAW\BOB\support\v1.2.8\Highlight_Source_v1.2.8_published.bundle`.

Nếu còn lỗi: recheck PID/port/build identity trước kết luận, không mặc định runtime đã nâng cấp. Reproduce ở queue copy. So group schedule_config với group Daily plan/snapshot, request selected count và daily_slots; kiểm tra JS cache/load generations. Không ghi live queue bằng borrowed snapshot; mọi sửa phải writable loader và merge protections.

## Deployment

Bộ cài đã build/inspect: `release/Highlight_Desktop_Test_Setup_v1.2.8.exe`, **705449472 bytes**, SHA256 `f0135aa94fd3cbc74519bcd6fba0ae4ac8e8f45ecbf0f035af97b5ec006d33e2`. Tag/source immutable `v1.2.8` tại `3cddca44e74556f217f7cdd0d825e61153c148cd`. Packaged identity sạch, Graph v24.0, 33 source files khớp, empty queue/credential seeds và không runtime state. Xem `installer_payload.json`.

**Đã phát hành GitHub v1.2.8**, release ID **404937985**, `draft=false`, `prerelease=true`. URL: https://github.com/minhpark89/Highlight_Video_Studio/releases/tag/v1.2.8. Toàn bộ ba assets installer/SHA256/checkpoint được tải đầy đủ không đăng nhập, HTTP200 và byte/hash khớp lúc **2026-10-06 23:48:42 +07**. Xem `release.json`, `deployment_status.json`, `public_download_verify.json`. Remote immutable tag/source và branch đã được kiểm tra. Source/tag giữ nguyên `3cddca44e74556f217f7cdd0d825e61153c148cd`; branch documentation có các commit mới hơn.

Checkpoint asset độc lập được chuẩn bị trước publication, nên phần trạng thái của nó ghi prepared; trạng thái cuối dùng evidence/latest branch. Source backup đầy đủ tại `E:\OPENCLAW\BOB\support\v1.2.8\Highlight_Source_v1.2.8_published.bundle`; installer/asset nằm trong `source-worktree/release/`. Không cài/sửa runtime thật hoặc gửi publish/delete Meta/CMS trong phiên.

Cách dùng: đóng app cũ, cài v1.2.8 vào đúng thư mục đang dùng. Mở NEW → Lên lịch → chọn **3 bài/Page** → xác nhận để lưu đủ ba giờ cho tương lai. Group config cũ có ba giờ nhưng Daily plan cũ hai giờ sẽ được modal hiển thị đúng; nâng cấp/GET không tự rewrite các lịch đã có.
