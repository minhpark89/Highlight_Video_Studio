import os, glob, re

# Boss nói: "Không ổn. Ấn 3 link thì 3 tab cmd đen hiện ra không thấy link được gán vào và thực hiện render"
# Hãy phân tích kỹ câu nói của boss:
# "Ấn 3 link thì 3 tab cmd đen hiện ra không thấy link được gán vào và thực hiện render"
# 1. Boss bấm vào đâu?
# - Boss tìm/cào link xong, thấy danh sách video.
# - Boss ấn vào 3 link đó (ví dụ click vào link tiêu đề của từng video, hoặc click nút nào đó).
# - Điều gì xảy ra? "3 tab cmd đen hiện ra không thấy link được gán vào và thực hiện render".
# Khoan! Tại sao lại là "tab cmd đen"?
# Có những khả năng:
# A. Boss click vào link video hoặc nút nào đó, mà trong Windows định dạng file hoặc protocol mở một cửa sổ CMD/terminal đen?
# B. Hay trên giao diện web có nút mở terminal?
# C. Hay trong News_Video_Studio hoặc Highlight_Video_Studio có hàm chạy lệnh hệ thống mở cmd?
# D. Hay boss click vào nút nào trên máy tính ngoài desktop?

# Hãy kiểm tra các file mã nguồn xem có chỗ nào gọi "cmd" hoặc mở terminal khi click vào link không!
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    h = f.read()

# Xem kỹ đoạn render từng video card cào được:
idx = h.find('container.innerHTML = results.map')
print("=== Research Results Card Template ===")
print(h[idx:idx+2500])

