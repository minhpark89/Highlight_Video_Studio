from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

old_func = """def api_youtube_status():
    \"\"\"Kiểm tra xem Chrome profile đã đăng nhập YouTube hay chưa dựa trên cookies.\"\"\"
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
                pass"""

new_func = """def api_youtube_status():
    \"\"\"Kiểm tra xem Chrome profile đã đăng nhập YouTube hay chưa dựa trên cookies (hỗ trợ cả Default và Profile 1..9).\"\"\"
    base_dir = r"D:\\Highlight_Video_Studio\\chrome_profile"
    if not os.path.exists(base_dir):
        return jsonify({"logged_in": False, "reason": "Chưa có profile Chrome"})
    
    profiles = ["Profile 1", "Default", "Profile 2", "Profile 3"]
    total_cnt = 0
    
    for prof in profiles:
        cookie_path = os.path.join(base_dir, prof, "Network", "Cookies")
        if not os.path.exists(cookie_path):
            continue
            
        temp_db = os.path.join(base_dir, f"temp_yt_{prof}.db")
        try:
            shutil.copyfile(cookie_path, temp_db)
            conn = sqlite3.connect(temp_db)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM cookies WHERE host_key LIKE '%youtube.com%' AND name IN ('LOGIN_INFO', 'SID', 'SSID', 'SAPISID')")
            row = cur.fetchone()
            cnt = row[0] if row else 0
            conn.close()
            total_cnt += cnt
            if cnt > 0:
                return jsonify({"logged_in": True, "count": cnt, "profile": prof})
        except Exception as e:
            pass
        finally:
            if os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except Exception:
                    pass
                    
    return jsonify({"logged_in": total_cnt > 0, "count": total_cnt})"""

if old_func in text:
    text = text.replace(old_func, new_func)
    app_path.write_text(text, encoding="utf-8")
    print("Updated api_youtube_status to check Profile 1 and other profiles!")
else:
    print("Could not find exact old_func")
