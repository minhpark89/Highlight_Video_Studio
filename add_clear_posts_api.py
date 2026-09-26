from pathlib import Path

# Add clear posts endpoint to web/app.py
app_py_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py_path.read_text(encoding="utf-8")

# Let's see where /api/posts is defined
find_str = '@app.route("/api/posts", methods=["GET"])'
pos = text.find(find_str)
print("Found /api/posts at pos:", pos)

new_routes = """@app.route("/api/posts/clear", methods=["POST"])
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
    })

"""

if "/api/posts/clear" not in text:
    text = text[:pos] + new_routes + text[pos:]
    app_py_path.write_text(text, encoding="utf-8")
    print("Added /api/posts/clear endpoint to app.py successfully!")
else:
    print("/api/posts/clear already exists!")
