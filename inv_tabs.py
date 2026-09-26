# Check what application or website boss was using
# Boss says: "Không ổn. Ấn 3 link thì 3 tab cmd đen hiện ra không thấy link được gán vào và thực hiện render"
# Let's check Chrome history or recent tabs or download history
import sqlite3, os, glob, shutil, tempfile

chrome_history_paths = glob.glob(r"C:\Users\Admin\AppData\Local\Google\Chrome\User Data\*\History")

for hp in chrome_history_paths:
    try:
        tmp = tempfile.mktemp()
        shutil.copyfile(hp, tmp)
        conn = sqlite3.connect(tmp)
        c = conn.cursor()
        c.execute("SELECT url, title, datetime(last_visit_time/1000000-11644473600, 'unixepoch', 'localtime') as visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 10")
        rows = c.fetchall()
        print(f"--- History from {hp} ---")
        for r in rows:
            print(f"  [{r[2]}] {r[1]} -> {r[0]}")
        conn.close()
        os.remove(tmp)
    except Exception as e:
        print(f"Error reading {hp}: {e}")

