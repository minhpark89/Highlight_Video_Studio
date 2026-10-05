# Checkpoint — kho video, upload trước lên Facebook và Post hàng ngày

Ngày: 2026-10-05 (Asia/Saigon).

## Phạm vi cuối cùng

Video có sẵn trong kho/output được nhận tự động, phân bổ cho nhóm Page đã tick, upload trước lên Facebook để Facebook giữ lịch và tự đăng. Website giữ luồng đã code: lấy video YouTube gốc dài và nhúng embed code vào bài Website; First Comment dẫn tới bài Website của chúng ta. Không bắt buộc upload MP4 lên Website hay thêm SSH.

Đã nối pipeline trong source `release/v1.1.9`:

- Render ghi vào tên tạm `.rendering.*.mp4`, chỉ đổi tên nguyên tử sang MP4 cuối khi FFmpeg thành công.
- `src/output_pipeline.py` quét `output`, bỏ qua file đang render, kiểm tra container bằng `ffprobe`, giữ SHA-256 ledger SQLite và claim slot/page bền vững qua restart, rename, delete/reimport.
- Video hoàn chỉnh tự tạo Content/LLM package một lần. Lỗi LLM vẫn đi qua fallback hiện có; lỗi CMS/video website giữ trạng thái chờ/lỗi.
- Có giới hạn backlog/disk pressure; producer render tạm dừng khi đầy, worker content và bài đã có lịch vẫn tiếp tục.
- Có API `/api/output-pipeline/settings`, `/status`, `/run`, `/plans` và `/api/posts/<id>/draft`.
- UI quy tắc lịch và modal phân bổ có checkbox **Post hàng ngày**, phạm vi Page/nhóm đã tick, chế độ duyệt tay → Draft hoặc tự động đăng/lên lịch.
- Draft có màn xem video, sửa title/caption/First Comment/Page/thời gian, lưu hoặc duyệt. Bản đã duyệt đóng băng nội dung; LLM trả muộn không ghi đè.
- Cleanup chỉ xóa MP4 local khi mọi post dùng chung đã published, có receipt/hash ledger, website video đã verified và không còn consumer đang dùng file.
- Website package ghi nhận `youtube_embed_verified` và tái sử dụng receipt embed cũ; CMS không bị gọi lại khi package Website/YouTube đã sẵn sàng.

Checkbox **Post hàng ngày** có ở quy tắc và modal nhóm. Nhóm được tick mới nhận clip; kho rỗng thì chờ, video mới xuất hiện thì tiếp tục. Chế độ tự động mặc định dùng `meta_scheduled` để upload trước; vẫn có lựa chọn duyệt tay hoặc App giữ lịch.

App cần mở khi nhận video mới và giao lịch; sau khi Meta đã nhận lịch, Facebook tự đăng dù tắt app. First Comment vẫn cần worker app chạy sau giờ đăng.

Kiểm thử cuối sau rà soát: `541 passed, 3 skipped, 29 subtests passed` (pytest toàn bộ, FFmpeg/ffprobe bundled trong PATH).

Test tích hợp xác nhận kho → package có YouTube gốc → Meta nhận lịch trước giờ đăng; vòng scheduler sau không upload lại. Browser QA offline lưu đúng nhóm/Page và `meta_scheduled`, không có lỗi JavaScript. Evidence: `E:/OPENCLAW/BOB/support/output-pipeline/evidence/`.

Bản `daily-stock1` là bản trước rà soát. Bản cài cuối: `E:/OPENCLAW/BOB/source-worktree/release/Highlight_Desktop_Test_Setup_v1.1.9-daily-stock2.exe` (681865216 bytes). SHA-256: `a4a280c7a7bd2ef1f37ba24188bdfd1f35978fcc6192acbbe00eefcf5281c352`. Đã đối chiếu payload với 10 file source runtime; các test release đã qua; seed không chứa token/credential/runtime state. Report: `support/output-pipeline/evidence/installer_verify.json` (ngoài source-worktree), script lặp lại `support/output-pipeline/verify_payload.ps1`.

Chưa cài bản này lên runtime đang dùng và chưa upload Facebook thật trong lượt này; test Meta dùng fixture. Không publish lên GitHub.

## Rà soát hoàn thành từng yêu cầu

Các yêu cầu Website MP4/SSH trong checkpoint cũ đã được thay bằng đính chính trực tiếp của người dùng: Website dùng YouTube gốc dài; Reels dùng clip kho để upload trước lên Meta.

| Yêu cầu | Kết quả và bằng chứng |
| --- | --- |
| MP4 hoàn chỉnh tự vào Content đúng một lần | `test_partial_growing_and_invalid_mp4_never_enters_queue`, probe FFmpeg thật và ledger crash recovery. Render chỉ expose tên cuối sau thành công. |
| Duyệt tay / tự động theo lựa chọn | `test_manual_draft_and_explicit_auto_transition_use_same_fallback`; Lưu Draft lưu cả Page/giờ, giữ Draft; duyệt dùng lại giá trị đã lưu. |
| Phân bổ sớm, ưu tiên queue, fallback hợp lệ | Slot được claim trước content; `test_assigned_daily_content_is_processed_before_unassigned_library_work` chạy worker thật; test tích hợp LLM timeout → fallback → Meta handoff. |
| Website giữ YouTube gốc và First Comment đúng URL | Test YouTube embed kiểm tra iframe/URL, không gọi upload MP4; package reuse legacy; URL nguồn được giữ trong claim khi file đổi tên. Lỗi CMS không mở trạng thái ready giả. |
| Chống trùng restart/rename/reimport/nhóm trùng | Ledger SHA/source identity/slot; test scan đồng thời, batch claim crash, manual save crash và slot conflict. Không tự chọn nhóm/lịch cũ để opt-in. |
| Chỉ cleanup sau published, hết consumer | Test tích hợp chạy scheduler → Meta schedule → published fixture → consumer running giữ file → consumer xong cleanup. Receipt chứa Meta ID được ghi trước unlink; package/website/history còn. |
| Bản đã duyệt bất biến, không đăng lại khi đối soát/dọn | Test stale post revision/LLM late; test tích hợp nhiều scheduler cycle vẫn chỉ một upload cho source cũ. |
| Liên tục, giới hạn backlog, kho rỗng chờ kho mới | Test producer expose metadata/queue clip 1 khi vẫn render clip 2; threshold disk/backlog và producer wait; selected-group empty-stock resume; test tích hợp cleanup/restart → clip mới phân bổ tiếp. |
| Tick hàng ngày được lưu/nạp/tắt đúng nhóm | Browser QA mở lại modal, giữ manual/app mode, đổi nhóm trả về default unchecked, bỏ tick tắt plan mà không tạo one-time batch. Kho rỗng lưu plan được, không gọi Meta. |

Rà soát bổ sung sửa: (1) modal nạp trạng thái riêng từng nhóm và chặn lưu khi đang tải; (2) bỏ tick tắt nhận clip mới, giữ bài đã có lịch; (3) Lưu Draft lưu Page/giờ và recovery revision đầy đủ qua lỗi JSON save; (4) ưu tiên content đã phân bổ trước library; (5) giữ URL nguồn/claim của clip renamed pending.

Browser QA: `support/output-pipeline/offline_ui_verify.py`, `evidence/ui_verify.json`, `daily_group_saved.png`. Không có pageerror. Build release nay có `tests/test_output_pipeline.py` trong các kiểm tra bắt buộc.
