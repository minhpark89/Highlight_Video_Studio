# Checkpoint v1.2.1 — quản lý theo nhóm, Draft gọn và First Comment

Ngày: 2026-10-06 (Asia/Saigon)

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
- Browser offline QA: `support/group-review1/evidence/ui_verify.json`; không có JavaScript error. Đã kiểm tra 800 clip kho, 65 Draft, 493 bài lịch sử, phân trang 50/30 dòng, duyệt batch 5 bài, tải detail riêng và lưu chế độ giữ lịch.
- Xác minh ba bài Website lỗi trên máy hiện tại: HTTP 200, không còn đoạn bị nhận nhầm, package cached là English, YouTube embed gốc tồn tại trên public article. Báo cáo: `support/group-review1/evidence/public_articles_verify.json`.
- Bộ cài: `release/Highlight_Desktop_Test_Setup_v1.2.1.exe`
- SHA-256 và source identity được xác minh ở `checkpoints/evidence/v1.2.1/installer_verify.json` và file `.sha256` cùng bộ cài.

## Cách dùng

1. Mở tab **Nhóm Trang & Lên Lịch**, chọn nhóm và bật **Post hàng ngày**. Nhóm mới mặc định `Duyệt tay → Draft`; có thể chọn tự động nếu muốn worker giao Meta theo lịch. Giữ lựa chọn tự động đã lưu của nhóm cũ.
2. Vào khung **Chuẩn bị & Draft theo nhóm** trong cùng tab. Bài chỉ xuất hiện sau khi đã được gắn Page, Token và giờ; không cần tìm trong toàn bộ lịch sử.
3. Mở một bài để sửa, kiểm tra First Comment/Website, rồi **Duyệt & lên lịch**. Với Meta giữ lịch, app upload trước để Facebook tự đăng đúng giờ.
4. Nếu Website lỗi, dùng **Thử lại Website** trên đúng bài. Không tạo URL CMS mới và không gửi lại Reel.

Bộ cài chưa tự cài đè runtime đang chạy và chưa đăng/xóa bài Meta thật. Installer sao lưu dữ liệu và giữ queue, token/Page mapping, cấu hình, output/ledger khi nâng cấp. Sau cài, dùng **Thử lại Website** cho ba bài bị chặn; app xác minh lại đúng URL.

## Lệnh kiểm tra và đóng gói

```powershell
$env:PATH = 'E:\OPENCLAW\BOB\Highlight destop test\bin;' + $env:PATH
python -m pytest -q --no-header
python checkpoints\tools\v1.2.1\offline_ui.py
.\build_release.ps1 -Version 1.2.1 -SkipTests -ToolSource 'E:\OPENCLAW\BOB\Highlight destop test\bin' -RuntimeSource 'E:\OPENCLAW\BOB\Highlight destop test\runtime' -IconSource 'E:\OPENCLAW\BOB\Highlight destop test\app.ico' -WhisperModelSource 'E:\OPENCLAW\BOB\Highlight destop test\models\faster-whisper-small'
powershell -NoProfile -File checkpoints\tools\v1.2.1\verify_payload.ps1
```
