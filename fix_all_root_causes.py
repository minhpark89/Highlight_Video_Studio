import json
import re
import os

print("=== 1. FIX APP.PY: load_jobs ROBUST PARSING & JOBS LOCK ===")
APP_PY_PATH = r'D:\Highlight_Video_Studio\web\app.py'
with open(APP_PY_PATH, 'r', encoding='utf-8') as f:
    app_text = f.read()

# Make load_jobs robust against concurrent partial writes or unescaped characters
new_load_jobs = '''JOBS_LOCK = threading.Lock()

def load_jobs():
    if not JOBS_FILE.exists():
        return []
    for _ in range(5):
        try:
            with open(JOBS_FILE, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
                if not content:
                    time.sleep(0.05)
                    continue
                # Try standard json parse first
                try:
                    return json.loads(content)
                except Exception:
                    # Fallback to strict=False or raw_decode to prevent empty queue bug
                    try:
                        return json.loads(content, strict=False)
                    except Exception:
                        decoder = json.JSONDecoder()
                        obj, _ = decoder.raw_decode(content)
                        return obj
        except Exception:
            time.sleep(0.05)
    return []

def save_jobs(jobs):
    with JOBS_LOCK:
        tmp_file = BASE_DIR / "jobs.tmp"
        for _ in range(10):
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(jobs, f, ensure_ascii=False, indent=2)
                # Atomic replace
                if tmp_file.exists():
                    os.replace(tmp_file, JOBS_FILE)
                return True
            except Exception:
                time.sleep(0.05)
        return False
'''

# Replace load_jobs in app.py
app_text = re.sub(r'def load_jobs\(\):.*?(?=\ndef |\Z)', new_load_jobs + '\n', app_text, flags=re.DOTALL, count=1)

with open(APP_PY_PATH, 'w', encoding='utf-8') as f:
    f.write(app_text)
print("Updated load_jobs & save_jobs in app.py with Lock & fallback recovery!")

print("=== 2. REPAIR JOBS.JSON CLEANLY ===")
JOBS_FILE = r'D:\Highlight_Video_Studio\jobs.json'
with open(JOBS_FILE, 'r', encoding='utf-8', errors='replace') as f:
    raw_jobs = f.read()

decoder = json.JSONDecoder()
try:
    obj, idx = decoder.raw_decode(raw_jobs.strip())
    print(f"Decoded {len(obj)} jobs from jobs.json.")
    with open(JOBS_FILE, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print("Cleaned jobs.json successfully!")
except Exception as e:
    print("Error decoding jobs:", e)

print("=== 3. UPDATE TEMPLATES: FIX BLOG LABEL ===")
for p in [r'D:\Highlight_Video_Studio\web\templates\index.html', r'D:\Highlight_Video_Studio\web\index.html']:
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            t = f.read()
        t = t.replace('Đính kèm link Blog bài viết (boostnews.danhngon.pro)', 'Đính kèm link bài viết Blog Website')
        t = t.replace('https://boostnews.danhngon.pro', 'https://yourblogdomain.com')
        with open(p, 'w', encoding='utf-8') as f:
            f.write(t)
        print(f"Updated blog label in {p}")

