from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

old_code = """@app.route("/api/posts/clear", methods=["POST"])
def api_clear_posts():
    data = request.get_json(silent=True) or {}
    status_filter = data.get("status", "all") # 'all' or 'scheduled'
    
    posts = load_json_file(POSTS_FILE, [])
    if status_filter == "scheduled":
        new_posts = [p for p in posts if p.get("status") != "scheduled"]
        removed_count = len(posts) - len(new_posts)
    else:
        removed_count = len(posts)
        new_posts = []
        
    save_json_file(POSTS_FILE, new_posts)
    return jsonify({
        "success": True, 
        "removed_count": removed_count,
        "message": f"Đã hủy và xóa {removed_count} bài đăng thành công!"
    })"""

new_code = """@app.route("/api/posts/clear", methods=["POST"])
def api_clear_posts():
    try:
        data = request.get_json(silent=True) or {}
        status_filter = data.get("status", "all") # 'all' or 'scheduled'
        
        posts = load_posts()
        if status_filter == "scheduled":
            new_posts = [p for p in posts if p.get("status") != "scheduled"]
            removed_count = len(posts) - len(new_posts)
        else:
            removed_count = len(posts)
            new_posts = []
            
        save_posts(new_posts)
        return jsonify({
            "success": True, 
            "removed_count": removed_count,
            "message": f"Đã hủy và xóa {removed_count} bài đăng thành công!"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "message": f"Lỗi: {str(e)}"}), 500"""

if old_code in text:
    text = text.replace(old_code, new_code)
    app_path.write_text(text, encoding="utf-8")
    print("Fixed api_clear_posts in app.py!")
else:
    print("Could not find exact old_code in app.py")
