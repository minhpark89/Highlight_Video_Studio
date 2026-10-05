# CHECKPOINT — Render output → chuẩn bị bằng LLM → Draft chờ duyệt

Ngày: 2026-10-05 (Asia/Saigon)
Branch: `release/v1.1.9`
Commit nền trước checkpoint: `61856d68e9056ef0f62b6e4aa1235fc556e48203` (`1.1.9-meta-cancel1`).

## Quyết định đã chốt cho phiên sau

Luồng mặc định phải là:

`MP4 hoàn chỉnh trong output đã cấu hình`
→ kiểm tra file và chống trùng
→ LLM tạo/hoàn thiện content package
→ upload video thật lên website/server (đây là đường chính)
→ tạo bài website, ảnh, player/video, caption và First Comment có URL bài website
→ kiểm tra URL/player và đánh dấu **Draft chờ duyệt**
→ người dùng duyệt
→ chọn **Đăng ngay** hoặc **Lên lịch ngày/giờ**
→ dùng các quy trình publish/scheduler hiện có của app.

Không được giao Meta lịch hoặc đăng trước khi draft được duyệt. Không tạo thêm thư mục output riêng theo Page; dùng thư mục output và đường dẫn đã cấu hình trong app. Reuse package đã sẵn sàng, không chạy lại LLM/upload khi reload hoặc retry nếu hash/package vẫn hợp lệ.

## Bằng chứng LoHaPage đã xác nhận

Nguồn: `support/lucas-lohapage-review/evidence/loha_transcript.txt` và các frame trong `support/lucas-lohapage-review/evidence/frames/`.

- Transcript 00:03:04–00:03:20: ở chế độ duyệt tay, bài import vào tool nằm ở **nháp**; người dùng bấm duyệt thì bài mới bắt đầu lên lịch và đăng.
- Transcript 00:03:32–00:03:45: chế độ tự động bỏ qua duyệt tay và đăng tự động.
- Transcript 00:04:02–00:05:12: có hai chế độ hẹn lịch:
  - Tool tự đăng: file còn trên máy, đến giờ app mới đăng, cần máy chạy.
  - Facebook tự đăng: tool đẩy bài lên Facebook ở trạng thái scheduled trước, tắt máy vẫn đăng theo lịch.
- Transcript 00:07:49–00:07:54: lịch có ngày và giờ cụ thể.
- Frame `contact_2.png` khoảng 03:30 hiển thị các thao tác **Duyệt & Đăng**, **Đăng ngay**, **Hẹn lịch**, **Chuyển nháp**, **Xóa** sau khi chọn bài.

Vì vậy có thể kết luận chắc chắn LoHaPage dùng mô hình import → draft khi bật duyệt tay → duyệt rồi đăng ngay hoặc hẹn lịch. Có thể kết luận họ có thao tác Đăng ngay và hẹn lịch ngày/giờ.

## Ranh giới bằng chứng

Tài liệu/video LoHaPage không chứng minh các điểm sau; không được ghi là tính năng đã xác nhận của LoHa:

- LoHa dùng LLM để viết content.
- LoHa upload video lên website trước khi tạo draft.
- LoHa tạo First Comment từ URL website.
- LoHa dùng website/player làm nguồn video chính.

LLM, upload website trước và First Comment là yêu cầu thiết kế đã chốt cho app của chúng ta. YouTube embed chỉ là phương án phụ khi người dùng/cấu hình chọn rõ; lỗi upload website phải giữ package chưa sẵn sàng, không được âm thầm thay bằng YouTube rồi báo hoàn tất.

MP4 hoàn chỉnh trong output là đầu vào bài Facebook. Hội thoại trước chưa chốt rõ video website là video gốc đầy đủ hay clip highlight; phiên sau cần đối chiếu cấu hình/metadata nguồn trước khi triển khai, không tự chọn nhầm video và không mặc định iframe YouTube thay cho upload.

## Hiện trạng source cần nhớ

- Bản `1.1.9-meta-cancel1` chỉ thêm hủy lịch Meta; chưa triển khai draft review pipeline.
- Tạo post hiện còn mặc định `status: scheduled` ở `web/app.py`; chưa có gate approval mặc định.
- App đã có Publish Now và chọn ngày/giờ/schedule Meta, nhưng publish hiện vẫn upload video tại thời điểm gọi, chưa chuẩn bị draft Facebook hoàn chỉnh.
- `/api/website/publish_draft` hiện còn ưu tiên YouTube; CMS endpoint presigned hiện được kiểm tra là image-only. Cần bổ sung/kiểm chứng đường upload video thật và public URL có player/Range trước khi đánh dấu package ready.

## Phạm vi triển khai phiên sau

Phạm vi người dùng nhấn mạnh: **thêm bước tự chuẩn bị và đưa vào draft trước**, sau đó dùng quy trình đăng/lên lịch của app. Tận dụng worker/content package/publisher hiện có; không viết lại toàn bộ scheduler hoặc thay đổi lịch cũ chỉ vì đổi mặc định của bài mới.

1. Thêm trạng thái draft và dữ liệu duyệt bền vững cho bài mới. Tách tiến độ chuẩn bị package khỏi trạng thái đăng nếu phù hợp cấu trúc hiện có; chỉ đánh dấu sẵn sàng duyệt sau khi đủ thành phần. Không tự đổi bài scheduled/meta_scheduled/published cũ sang draft.
2. Bắt file render hoàn chỉnh trong output an toàn (`.part` hoặc file tạm rồi rename atomically), ffprobe/metadata/hash/dedupe.
3. Worker LLM tạo package idempotent: website article, image, video upload, caption, First Comment, nguồn và checksum.
4. Verify website URL, video URL/player, quyền truy cập và First Comment URL; thiếu phần nào thì giữ preparing/needs_attention, không xếp lịch.
5. UI draft để xem video, bài website/ảnh/player, caption, First Comment, Page/group, token binding và thời gian; có Approve, Edit, Delete.
6. Sau Approve mới gọi luồng hiện có cho Đăng ngay hoặc Lên lịch ngày/giờ, gồm lựa chọn tool tự đăng hay Meta giữ lịch nếu phù hợp; giữ idempotency/retry và không upload trùng.
7. Scheduler và First Comment queue phải bỏ qua draft chưa duyệt. Xóa draft là thao tác local; draft không có remote Meta ID, không gọi chức năng hủy lịch Meta. Giữ nguyên hủy lịch cho bài đã giao Meta.
8. Kiểm thử: auto-import một MP4 tạo đúng một draft; restart không tạo lại; website upload chính có URL/player; First Comment đúng URL; Meta không có bài trước duyệt; Approve+Now và Approve+Schedule hoạt động; batch nhiều Page/ngày không trùng; YouTube chỉ dùng fallback.

## Trạng thái checkpoint

Checkpoint này chỉ ghi yêu cầu, bằng chứng và kế hoạch triển khai. Chưa sửa code pipeline và chưa phát hành installer mới.

Bản hủy lịch đã hoàn tất được ghi tại `E:/OPENCLAW/BOB/CODEX_CHECKPOINT_META_CANCEL1.md`. Chưa có bằng chứng 30 lịch thật trên PC khác đã được hủy; không ghi chúng đã xử lý trong checkpoint draft này. Không tự chạy POST/DELETE Meta hoặc publish website thật chỉ để kiểm tra checkpoint.

