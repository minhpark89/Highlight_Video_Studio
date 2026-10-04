
## 7. Bổ sung 04/10/2026 — Meta handoff cho lịch app

- Commit source mới: 217f37a (eat: hand off app schedules to Meta).
- Đã thêm API POST /api/posts/handoff-meta và worker handoff an toàn. Chọn từng bài hoặc hàng loạt trong Quản lý Bài Đăng; giữ nguyên post ID/Page/token/video/giờ lịch/First Comment. Handoff chỉ nhận bài scheduled còn hơn 10 phút, trong 29 ngày, Website + First Comment + video đã sẵn sàng và credential gốc còn xác minh được.
- Trạng thái UI mới: App giữ lịch · chưa gửi Meta (cần app chạy khi đến giờ), Chờ gửi lên Meta, Đang gửi video lên Meta, Meta giữ lịch · chờ đăng (video tự đăng dù tắt app), Meta đã đăng, và First Comment luôn ghi rõ cần app chạy sau giờ đăng.
- Handoff idempotent: lưu ID upload trước transfer/finish; kết quả mơ hồ giữ processing để đối soát, không upload lại. Meta từ chối trước upload trả bài về App giữ lịch.
- Xóa lịch local bị khóa khi bài đã giao/đang xử lý/Meta đã nhận; không giả vờ hủy lịch Meta.
- Bản cài desktop-test: [Highlight_Desktop_Test_Setup_v1.1.8-meta-handoff4.exe](release/Highlight_Desktop_Test_Setup_v1.1.8-meta-handoff4.exe), SHA-256 $hash, kích thước $size bytes. Build từ source sạch commit 217f37a.
- QA: full suite 335 passed, 3 skipped, 29 subtests; release build gates passed; browser fixture QA support/meta-handoff4/evidence/ui_results.json không có page error, kiểm tra desktop 1600px và 1280px, không gọi Meta thật.
- Runtime hiện tại vẫn giữ nguyên **100 scheduled + 100 published**; chưa tự động chuyển 100 bài mới lên Meta. Operator chọn các bài đủ điều kiện rồi bấm Đưa bài đã chọn lên Meta chờ hoặc Đưa tất cả ....
- Ghi checkpoint lúc $now.
