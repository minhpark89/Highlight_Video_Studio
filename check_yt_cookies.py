import sqlite3
import shutil
import os

for prof in ["Default", "Profile 1"]:
    cpath = rf"D:\Highlight_Video_Studio\chrome_profile\{prof}\Network\Cookies"
    if os.path.exists(cpath):
        tmp = rf"D:\Highlight_Video_Studio\temp_{prof}.db"
        try:
            shutil.copyfile(cpath, tmp)
            conn = sqlite3.connect(tmp)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM cookies WHERE host_key LIKE '%youtube.com%' AND name IN ('LOGIN_INFO', 'SID', 'SSID', 'SAPISID')")
            cnt = cur.fetchone()[0]
            print(f"Profile {prof} YouTube auth cookies count:", cnt)
            conn.close()
        except Exception as e:
            print(f"Profile {prof} error:", e)
        finally:
            if os.path.exists(tmp): os.remove(tmp)
    else:
        print(f"Profile {prof} does not exist")
