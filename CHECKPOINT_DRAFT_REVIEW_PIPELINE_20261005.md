# CHECKPOINT — Output → LLM → Draft hoặc tự đăng theo nhóm → xóa clip đã đăng

Ngày: 2026-10-05 (Asia/Saigon).
Branch: `release/v1.1.9`.
Commit code nền: `61856d68e9056ef0f62b6e4aa1235fc556e48203` (`1.1.9-meta-cancel1`).
Checkpoint ban đầu: commit tài liệu `ddb6ce5`. Bản cập nhật này thay thế yêu cầu mọi bài đều phải duyệt tay: hỗ trợ cả duyệt tay và tự động theo lựa chọn của người dùng.

## Yêu cầu mới nhất đã chốt

1. LLM tạo nội dung là phần riêng của app chúng ta. Người dùng xác nhận LoHaPage không có phần này; không cần nghiên cứu LoHa để quyết định cách tích hợp LLM.
2. Chỉ cần video render hoàn chỉnh xuất hiện trong `output` đã cấu hình thì app tự đưa vào hàng đợi LLM/content. Không thêm thư mục riêng cho từng Page và không yêu cầu import thủ công cho mỗi lượt render.
3. LLM/content worker thực hiện quy trình hiện có: chuẩn bị caption, bài website, ảnh, upload video thật lên website/server, player và First Comment có đúng URL bài website. Upload video website là đường chính; YouTube embed là phương án phụ được chọn rõ.
4. Hỗ trợ **duyệt tay** và **tự động đăng**:
   - Duyệt tay: package hoàn tất → Draft mặc định để xem/sửa → người dùng duyệt và chọn đăng ngay hoặc ngày/giờ.
   - Tự động: khi đã bật cho nhóm/luồng, phân bổ clip vào nhóm Page có sẵn, hoàn tất package hoặc fallback hợp lệ, rồi tự đăng/lên lịch theo quy trình app. Không yêu cầu duyệt từng bài trong chế độ này.
5. Có thể phân bổ/đặt chỗ clip vào nhóm trước khi LLM xong. Hàng đợi đăng ưu tiên xử lý package của các bài đó, tiếp tục/thử lại LLM có giới hạn; LLM lỗi/quota/timeout thì dùng **fallback no-LLM hiện có** để tiếp tục. Không buộc người dùng chờ một lượt LLM mới để phân bổ nhóm.
6. Phân bổ số lượng lớn qua các nhóm Page có sẵn, giữ chống trùng giữa clip/nhóm/Page và qua restart/retry. Một clip được claim một lần trong luồng phân bổ; không tự nhân bản toàn bộ folder cho mọi Page.
7. Mục tiêu vận hành: render → xử lý → đăng → xóa video local đã hoàn tất để giải phóng `output` cho lượt render tiếp theo. Không chỉ tích lũy hàng trăm clip trong folder mà không tiêu thụ/dọn.

## Luồng triển khai cần đạt

`MP4 hoàn chỉnh trong output`
→ claim/hash/dedupe bền vững
→ enqueue hoặc reuse content package bằng LLM
→ có thể phân bổ sớm vào nhóm Page, đánh dấu đang chờ content
→ upload video website + bài/ảnh/player + caption + First Comment
→ package ready (LLM hoặc no-LLM fallback)
→ Draft khi duyệt tay / queue đăng khi đã bật tự động
→ đăng ngay hoặc lịch theo quy trình app
→ xác minh đã đăng, lưu lịch sử chống trùng
→ xóa video local khi không còn tác vụ cần file.

Mặc định vẫn có Draft khi chưa chọn tự động. Chế độ tự động được cấu hình rõ và lưu cùng job/post, không tự bật cho các nhóm/lịch cũ. Việc phân bổ sớm vào nhóm chỉ là đặt chỗ và xếp hàng; gọi Meta khi package/fallback đã đáp ứng điều kiện đăng. Khi ở chế độ duyệt tay, phân bổ sớm không tự duyệt bài.

## Fallback và đồng thời

- Phân biệt LLM chưa xong với LLM đã lỗi. Nếu package đang running thì ưu tiên/tiếp tục job đang có, không tạo job LLM thứ hai cho cùng video. Retry theo timeout/giới hạn/circuit breaker hiện có, tránh gọi LLM vô hạn.
- Fallback no-LLM là caption/article/comment theo template/metadata hiện có, không phải bỏ qua upload video website, đăng caption rỗng hoặc First Comment sai URL. Nếu website/upload video thực sự lỗi thì giữ trạng thái lỗi/chờ xử lý; lỗi LLM có thể fallback, lỗi website không được báo ready giả.
- Khi bài đã chuẩn bị đăng, đóng băng phiên bản nội dung và First Comment đã chọn. Kết quả LLM về muộn không ghi đè bản đã duyệt/đã claim/đã đăng hoặc gây thêm bài/comment.
- Duyệt tay áp dụng cho cả package LLM và package fallback. Tự động dùng package hợp lệ và tiếp tục theo quy tắc nhóm mà không cần duyệt từng bài.

## Chống trùng và dọn video

- Giữ ledger bền vững của source identity, hash, package ID, group/Page assignment và Meta IDs; không dùng việc file còn tồn tại làm lịch sử đăng.
- Chống trùng phải tính cả preparing/draft/reserved/scheduled/meta_handoff/meta_scheduled/processing/publishing/published. Đổi tên file, restart, hai nhóm cùng nhận clip hoặc worker quét lại không được tạo thêm bài.
- Ghi receipt/ledger trước khi xóa file. Clip bị xóa rồi render/import lại vẫn được nhận diện để tránh đăng lại ngoài ý muốn.
- Chỉ xóa **video local trong output đã cấu hình**. Không xóa video trên website, bài website, URL, package hoặc lịch sử chống trùng.
- Với chế độ đăng ngay: xác minh Meta đã published, website video đã upload và có URL/player, mọi consumer cần file (LLM, trích ảnh, upload website, các post dùng chung) đã xong thì xóa MP4 local.
- Không xóa clip còn đang render/LLM đọc/upload/retry/draft chưa duyệt hoặc có bài dùng chung chưa hoàn tất. Với Meta giữ lịch, mặc định đợi published; muốn xóa trước giờ đăng phải có chính sách riêng dựa trên bản server đã kiểm chứng và khả năng phục hồi, không dựa chỉ vào POST accepted.
- First Comment retry có thể tiếp tục sau khi xóa MP4 nếu chỉ cần URL/text/Meta ID, không giữ clip chỉ vì đang chờ comment.
- Xóa lỗi do file lock thì retry cleanup riêng, không đăng lại. Kiểm tra absolute resolved path còn trong output trước unlink; không dọn cả folder bằng recursive delete.
- Có giới hạn backlog theo dung lượng trống/số clip đang xử lý và concurrency hiện có. Khi render nhanh hơn upload/post, điều tiết/pause producer hoặc báo rõ; không xóa video chưa đăng để lấy chỗ.

## Source hiện tại và phần cần nối

- Bản `1.1.9-meta-cancel1` bổ sung hủy lịch Meta; chưa có watcher/output → auto content → draft/auto group hoàn chỉnh.
- `web/app.py`, `/api/distribute/batch`: đã phân bổ clip khác nhau cho Page trong nhóm, lọc clip trong ledger/queue, ưu tiên package ready, tạo row `scheduled` và enqueue/reuse content package ở background. Cần nối với auto-import/draft và claim chống trùng cho các trạng thái mới; không viết lại toàn bộ scheduler.
- `src/content_packages.py`: `generate_package(mode=auto)` đã có `no_llm_error_fallback`, `no_llm_quota_fallback`, `no_llm_circuit_open`; `mode=llm` thuần vẫn báo lỗi. Có queue, attach/reuse và retry. Tận dụng các nhánh này, lưu rõ nguồn kết quả và lý do fallback.
- `web/scheduled_publisher.py`: đã chặn Meta khi website/First Comment chưa sẵn sàng. `remove_posted_clip_file` đã kiểm tra path trong output, mọi post cùng file đã published/có Facebook ID và ledger, rồi unlink; vòng scheduler ghi `local_video_deleted_at`. Cần mở rộng guard cho content/render/upload consumers và website video thật.
- Chống trùng hiện tại chủ yếu qua path/tên file trong `posted_clips.json` và post rows; không mặc định đã có dedupe hash đầy đủ cho auto-import của canonical output.
- `/api/website/publish_draft` và luồng website hiện còn ưu tiên YouTube; endpoint presigned được kiểm tra là image-only. Bổ sung/kiểm chứng upload video thật và public video URL/player/Range trước khi ready.
- MP4 output là đầu vào bài Facebook. Loại video website (video gốc đầy đủ hoặc clip highlight) từng chưa được chốt rõ; đối chiếu cấu hình/metadata nguồn trước triển khai, không tự chọn nhầm nguồn hoặc thay upload bằng iframe YouTube.

## Bằng chứng LoHaPage đã đủ để tham khảo UI

Video: https://www.youtube.com/watch?v=9raXKJkjqkM

- Transcript 03:04–03:20: import vào nháp khi bật duyệt tay, duyệt rồi mới lên lịch/đăng.
- Transcript 03:32–03:45: chế độ tự động bỏ qua duyệt tay.
- Frame `support/lucas-lohapage-review/evidence/frames/contact_2.png`, khoảng 03:30: Duyệt & Đăng, Đăng ngay, Hẹn lịch, Chuyển nháp, Xóa.
- Transcript 04:02–05:12: tool giữ lịch cần máy chạy; Facebook giữ lịch upload trước và tự đăng.
- Transcript 07:49–07:54: lịch có ngày/giờ.
- Transcript 08:20–09:17: archive/xóa file đã đăng, chống trùng.

LLM là phần riêng của app theo xác nhận của người dùng. Video demo không xác nhận LoHa upload website/First Comment; không gán những phần này cho LoHa.

## Phạm vi và nghiệm thu phiên sau

Ưu tiên nối các bước đã có thành pipeline liên tục: tự lấy output → LLM/fallback → phân bổ nhóm → draft hoặc tự đăng → cleanup. Giữ lịch cũ, token/Page mapping, retry/handoff/cancellation hiện có.

Kiểm tra cần có:

1. MP4 đang render không bị lấy; MP4 hoàn chỉnh tự vào queue đúng một lần, kể cả quét lại/restart.
2. Duyệt tay giữ bài ở draft; tự động phân bổ nhóm và đăng khi ready mà không yêu cầu duyệt từng bài.
3. Package còn pending vẫn phân bổ sớm được; worker ưu tiên tiếp tục, không tạo LLM job trùng; lỗi/quota/timeout chuyển fallback no-LLM đúng quy trình.
4. Upload video website là đường chính; ảnh/player/bài/First Comment đúng nguồn/URL; website lỗi không được ngụy trang thành LLM fallback thành công.
5. Không trùng clip giữa các nhóm/Page hoặc sau rename/delete/reimport; claim/ledger bền vững qua restart.
6. Sau xác minh published và hết consumer, MP4 local được xóa; website/package/history còn; file shared, draft, pending, upload hoặc Meta processing chưa bị xóa.
7. LLM về muộn/cleanup retry không ghi đè nội dung đã đăng và không tạo bài/comment thứ hai.
8. Backlog lớn và disk pressure được điều tiết; không cần producer render hết kho mới bắt đầu post.

## Trạng thái bàn giao

Lượt này chỉ cập nhật checkpoint theo yêu cầu mới, chưa sửa code pipeline, chưa xóa video thật và chưa build/publish installer mới.

Bản hủy lịch đã hoàn tất: `E:/OPENCLAW/BOB/CODEX_CHECKPOINT_META_CANCEL1.md`. Chưa có bằng chứng 30 lịch thật trên PC khác đã được hủy. Không dùng checkpoint này làm bằng chứng đã triển khai pipeline hoặc đã xử lý các lịch thật đó.
