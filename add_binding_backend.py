import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
APP_PATH = BASE_DIR / "web" / "app.py"

with open(APP_PATH, "r", encoding="utf-8") as f:
    code = f.read()

# Route cập nhật gán Nhóm & Token cho 1 page hoặc hàng loạt page
update_binding_route = """
@app.route("/api/pages/update_binding", methods=["POST"])
def api_update_page_binding():
    data = request.json or {}
    page_id = str(data.get("page_id", "")).strip()
    group_id = str(data.get("group_id", "")).strip()
    token_id = str(data.get("token_id", "")).strip()

    if not page_id:
        return jsonify({"success": False, "error": "Thiếu page_id"}), 400

    pages = page_manager.list_pages()
    groups = page_manager.list_groups()
    tokens = token_vault.list_tokens(mask=False)

    target_page = next((p for p in pages if str(p.get("page_id") or p.get("id")) == page_id), None)
    if not target_page:
        return jsonify({"success": False, "error": "Không tìm thấy Fanpage"}), 404

    # 1. Cập nhật nhóm
    if group_id:
        matched_grp = next((g for g in groups if g.get("id") == group_id or g.get("name") == group_id), None)
        if matched_grp:
            target_page["group_ids"] = [matched_grp.get("id")]
            target_page["group_name"] = matched_grp.get("name")
            # Cập nhật page_id vào group nếu chưa có
            p_ids = matched_grp.get("page_ids", [])
            if page_id not in p_ids:
                p_ids.append(page_id)
                matched_grp["page_ids"] = p_ids
                page_manager.save_groups(groups)
    else:
        target_page["group_ids"] = []
        target_page["group_name"] = "Chưa nhóm"

    # 2. Cập nhật token
    if token_id:
        matched_tok = next((t for t in tokens if str(t.get("id")) == token_id), None)
        if matched_tok:
            target_page["token_id"] = token_id
            target_page["token_name"] = matched_tok.get("name", "System User")
            if matched_tok.get("token"):
                target_page["page_token"] = matched_tok.get("token")
    else:
        target_page["token_id"] = ""
        target_page["token_name"] = "AutoPool (Tự động)"

    page_manager.save_pages(pages)
    return jsonify({
        "success": True, 
        "message": f"Đã cập nhật Nhóm '{target_page.get('group_name')}' & Token '{target_page.get('token_name')}' cho trang {target_page.get('page_name')}!"
    })
"""

if "def api_update_page_binding" not in code:
    pos_route = code.find("@app.route(\"/api/pages/assign_token\"")
    if pos_route != -1:
        code = code[:pos_route] + update_binding_route + "\n\n" + code[pos_route:]
        with open(APP_PATH, "w", encoding="utf-8") as f:
            f.write(code)
        print("Injected api_update_page_binding route into app.py!")
    else:
        print("pos_route not found!")
else:
    print("api_update_page_binding already exists!")
