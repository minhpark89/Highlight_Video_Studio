# Highlight Desktop Test v1.2.2

- Thêm nút **Đăng lại bằng App** cho lỗi khởi tạo Meta bị từ chối chắc chắn, chưa có Meta ID; kiểm tra video, Website và First Comment trước khi xếp hàng.
- Hiển thị lịch Meta quá giờ và đồng bộ lại quyền Page/Token để kiểm tra cùng Video ID. Giữ chốt chống đăng trùng và receipt cũ.
- Luồng chuẩn bị hằng ngày tạo Website khi cache trước đó chỉ có text; cách ly một gói non-English để các gói hợp lệ tiếp tục. Khung Draft theo nhóm hiển thị backlog/lỗi pipeline.

Kiểm chứng: **608 passed, 4 skipped, 29 subtests passed**; browser offline 7 checks, không có JavaScript error. Payload bộ cài được đối chiếu source trước khi phát hành, kiểm tra không chứa queue/token/state người dùng.

Lỗi Facebook `368/4854002` vẫn cần quản trị viên xác minh danh tính. Sau nâng cấp, dùng **Kiểm tra Meta** và **Đồng bộ quyền và kiểm tra lại** trước khi phục hồi bài có ID. Bài đã published không đăng lại.

Bộ cài chưa tự cài vào runtime đang dùng. Checkpoint đính kèm ghi source commit, bằng chứng, cách backup và cách session sau tiếp tục fix.