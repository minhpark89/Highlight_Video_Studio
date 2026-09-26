from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect api_batch_assign_token
pos = text.find("def api_batch_assign_token():")
pos_end = text.find("@app.route", pos + 20)

old_func = text[pos:pos_end].strip()
print("=== OLD api_batch_assign_token ===")
print(old_func)

# Enhanced api_batch_assign_token that supports both single token_id and list of assignments: [{page_id, token_id}, ...]
new_func = """def api_batch_assign_token():
    data = request.json or {}
    pages = page_manager.list_pages()
    count = 0

    # 1. Hỗ trợ dạng mảng gán chi tiết từng page (round-robin assignments)
    assignments = data.get("assignments")
    if isinstance(assignments, list) and assignments:
        assign_map = {str(a.get("page_id")): str(a.get("token_id")) for a in assignments if a.get("page_id") and a.get("token_id")}
        for p in pages:
            pid = str(p.get("page_id"))
            if pid in assign_map:
                p["token_id"] = assign_map[pid]
                count += 1
        page_manager.save_pages(pages)
        return jsonify({"success": True, "count": count, "message": f"Đã tự động xoay vòng chia đều token cho {count} trang."})

    # 2. Hỗ trợ dạng gán 1 token_id cho danh sách page_ids
    token_id = str(data.get("token_id", ""))
    page_ids = [str(pid) for pid in data.get("page_ids", [])]
    if not token_id:
        return jsonify({"error": "Thiếu token_id hoặc danh sách phân bổ assignments"}), 400

    for p in pages:
        if str(p.get("page_id")) in page_ids:
            p["token_id"] = token_id
            count += 1

    page_manager.save_pages(pages)
    return jsonify({"success": True, "count": count, "message": f"Đã gán cứng Token cho {count} trang."})"""

text = text[:pos] + new_func + "\n\n\n" + text[pos_end:]
app_py.write_text(text, encoding="utf-8")
print("Updated api_batch_assign_token in web/app.py successfully!")
