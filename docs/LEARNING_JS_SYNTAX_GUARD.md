# BÀI HỌC VỀ GIAO DIỆN & TỰ ĐỘNG KIỂM TRA CÚ PHÁP TRÊN APP 5080 (HIGHLIGHT VIDEO STUDIO)
Ngày: 2026-09-25

## 1. Bản chất sự cố
- Khi chèn hoặc thay thế các khối giao diện JavaScript (render thẻ Card, Modal) trong `index.html`, nếu file HTML có các hàm trùng tên hoặc đóng ngoặc nhọn dư/thiếu (`SyntaxError: Unexpected token '}'` hoặc `SyntaxError: Identifier already declared`), toàn bộ trình duyệt sẽ ngừng thực thi khối script chính.
- Hậu quả: Hàm `switchTab()` và các bộ lắng nghe sự kiện `click` không được gắn vào các nút trên navbar, khiến app bị "đơ" cố định ở tab mặc định (Research Nguồn Link) và bấm sang các tab khác không phản hồi.

## 2. Quy tắc bắt buộc trước khi restart app
1. Tuyệt đối KHÔNG restart server nếu chưa chạy kiểm tra cú pháp JS.
2. Quy trình kiểm tra bắt buộc:
   ```bash
   python -c "with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8') as f: html=f.read(); import re; s=re.findall(r'<script\b[^>]*>([\s\S]*?)</script>', html); open(r'D:\Highlight_Video_Studio\temp_check_script_now.js', 'w', encoding='utf-8').write(s[0])"
   node --check D:\Highlight_Video_Studio\temp_check_script_now.js
   ```
3. Chỉ khi lệnh `node --check` trả về mã 0 (sạch lỗi 100%) mới được phép khởi động lại server app 5080.
4. Luôn kiểm tra các khối modal nhúng để đảm bảo không để rơi vãi form thừa hoặc các cặp thẻ `<div>` không đóng đúng vị trí.
