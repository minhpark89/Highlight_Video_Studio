import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
with open(BASE_DIR / "web" / "app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Make sure when a group is created or deleted, pages are synced with their group_name
old_save_group = """def api_save_group():
    data = request.json or {}
    group_id = data.get("id")
    name = data.get("name", "").strip()
    page_ids = data.get("page_ids", [])
    folder_binding = data.get("folder_binding") or data.get("folder_path") or str(OUTPUT_DIR)
    schedule_config = data.get("schedule_config")
    if not name:
        return jsonify({"error": "Tên nhóm không được để trống"}), 400
    
    group = page_manager.add_or_update_group(group_id, name, page_ids, folder_binding, schedule_config)
    return jsonify({"success": True, "group": group})

@app.route("/api/groups/<group_id>", methods=["DELETE"])
def api_delete_group(group_id):
    ok = page_manager.delete_group(group_id)
    return jsonify({"success": ok})"""

new_save_group = """def api_save_group():
    data = request.json or {}
    group_id = data.get("id")
    name = data.get("name", "").strip()
    page_ids = data.get("page_ids", [])
    folder_binding = data.get("folder_binding") or data.get("folder_path") or str(OUTPUT_DIR)
    schedule_config = data.get("schedule_config")
    if not name:
        return jsonify({"error": "Tên nhóm không được để trống"}), 400
    
    group = page_manager.add_or_update_group(group_id, name, page_ids, folder_binding, schedule_config)
    gid = group.get("id")

    # Đồng bộ tên nhóm trực tiếp vào từng page trong pages.json để hiển thị tức thì
    try:
        pages = page_manager.list_pages()
        pages_updated = False
        pid_set = set(str(pid) for pid in page_ids)
        for p in pages:
            cur_pid = str(p.get("page_id") or p.get("id"))
            if cur_pid in pid_set:
                p["group_name"] = name
                g_ids = p.get("group_ids", [])
                if gid not in g_ids:
                    g_ids.append(gid)
                p["group_ids"] = g_ids
                pages_updated = True
        if pages_updated:
            page_manager.save_pages(pages)
    except Exception as ex:
        print("[Error syncing group to pages]", ex)

    return jsonify({"success": True, "group": group})

@app.route("/api/groups/<group_id>", methods=["DELETE"])
def api_delete_group(group_id):
    ok = page_manager.delete_group(group_id)
    if ok:
        # Gỡ nhóm khỏi các page đang mang nhóm này
        try:
            pages = page_manager.list_pages()
            pages_updated = False
            for p in pages:
                g_ids = p.get("group_ids", [])
                if group_id in g_ids or p.get("group_id") == group_id:
                    p["group_ids"] = [g for g in g_ids if g != group_id]
                    p["group_name"] = "Chưa nhóm"
                    pages_updated = True
            if pages_updated:
                page_manager.save_pages(pages)
        except Exception as ex:
            print("[Error cleaning group from pages]", ex)
    return jsonify({"success": ok})"""

if old_save_group in code:
    code = code.replace(old_save_group, new_save_group)
    with open(BASE_DIR / "web" / "app.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("Updated api_save_group and api_delete_group with full page sync!")
else:
    print("Warning: old_save_group signature not matched verbatim.")
