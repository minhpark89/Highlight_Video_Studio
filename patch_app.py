import re, sqlite3, shutil, os

# Thêm API /api/system/youtube_status vào app.py
with open(r"D:\Highlight_Video_Studio\web\app.py", "r", encoding="utf-8") as f:
    content = f.read()

yt_status_code = '''
@app.route("/api/system/youtube_status", methods=["GET"])
def api_youtube_status():
    """Kiểm tra xem Chrome profile đã đăng nhập YouTube hay chưa dựa trên cookies."""
    cookie_path = r"D:\\Highlight_Video_Studio\\chrome_profile\\Default\\Network\\Cookies"
    if not os.path.exists(cookie_path):
        return jsonify({"logged_in": False, "reason": "Chưa có profile Chrome"})
    
    temp_db = r"D:\\Highlight_Video_Studio\\chrome_profile\\temp_yt_check.db"
    try:
        shutil.copyfile(cookie_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cookies WHERE host_key LIKE '%youtube.com%' AND name IN ('LOGIN_INFO', 'SID', 'SSID', 'SAPISID')")
        cnt = cur.fetchone()[0]
        conn.close()
        return jsonify({"logged_in": cnt > 0, "count": cnt})
    except Exception as e:
        return jsonify({"logged_in": False, "error": str(e)})
    finally:
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except Exception:
                pass

'''

if "/api/system/youtube_status" not in content:
    # Chèn trước api_open_chrome
    content = content.replace('@app.route("/api/system/open_chrome", methods=["POST"])', yt_status_code + '@app.route("/api/system/open_chrome", methods=["POST"])')
    with open(r"D:\Highlight_Video_Studio\web\app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Added /api/system/youtube_status successfully")
else:
    print("API already exists")
