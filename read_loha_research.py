import json

# Check lohapage image description or inspect the 4 panels
# In input-6f407596-476e-425e-a685-c25bd723ee70.jpg:
# Top Left: Quản lý token - table with columns: ID, Tên, Token, Số luồng, Thao tác, Trạng thái...
# Top Right: Nhóm trang - table or card rows with columns: Tên nhóm, Thư mục, Số trang, Hành động (Quét, Lên lịch, Sửa, Xóa)...
# Let's inspect the exact layout of LoHa Page from research docs
with open(r"F:\openclaw\.openclaw\workspace\research\lohapage_systemuser\PHAN_TICH_LOHAPAGE.md", "r", encoding="utf-8") as f:
    print(f.read()[:2000])
