# Highlight Desktop Test v1.2.3

Chọn lịch hôm nay cho bài đang chuẩn bị và Draft ngay trong Nhóm Trang. Có xem trước rồi áp dụng cho bài đã chọn, cả nhóm hoặc video lấy từ kho; hiển thị ngày, giờ cuối và số bài còn chỗ. Bài đang chuẩn bị tiếp tục làm nội dung/Website trước khi đăng. Bài vượt sức chứa giữ lịch cũ; lịch hôm nay không tự tràn sang ngày mai.

Giữ đúng Page–Token, source claim và nội dung. Daily tạm ngừng phân bổ thêm cho nhóm trong ngày sau thao tác cả nhóm/lấy kho, tiếp tục ngày sau. Bài chưa gửi Meta mà không kịp ngày đã chọn chờ hẹn lại. Bao gồm sửa cache Website/non-English, retry Init bị từ chối chắc chắn và kiểm tra lại Meta ID từ v1.2.2.

Validation: 632 passed, 4 skipped, 29 subtests passed; 9 browser checks không có lỗi JavaScript. Replay riêng dữ liệu thật xếp được 294 bài NEW vào hôm nay, giữ nguyên trạng thái/nội dung/binding và các bài remote. Đọc checkpoint kèm theo để biết source identity, build và cách tiếp tục sửa lỗi.

Khi nâng cấp, đóng app khi không có upload đang chạy và sao lưu dữ liệu. Bản cài giữ dữ liệu local. Lịch đã gửi Meta và bài đã đăng cần kiểm tra đúng ID; không đăng lại chỉ vì quá giờ. Quyền Meta bị chặn hoặc yêu cầu xác minh Facebook vẫn cần xử lý ở tài khoản.

## Dùng bản test

Sau khi cài, chọn **NEW → Cả nhóm hôm nay → Xem trước → Áp dụng lịch hôm nay**. Chọn giờ cách hiện tại khoảng 30 phút. Dùng **Lấy từ kho cho hôm nay** để đưa video chưa phân bổ vào nhóm. Chọn **Tự lên lịch khi sẵn sàng** nếu muốn tự đăng sau khi nội dung/Website hoàn tất; chế độ manual cần duyệt Draft.

Ba asset: bộ cài `.exe`, checksum `.sha256`, và **CODEX_CHECKPOINT_v1.2.3.md**. Checkpoint gồm nguyên nhân, file cần sửa theo triệu chứng, test liên quan, source identity và cách giữ dữ liệu/Meta IDs. Source và checkpoint cập nhật nằm trên nhánh `release/v1.2.3`; tag `v1.2.3` cố định ở source đóng gói.
