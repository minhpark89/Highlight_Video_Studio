import json
import re

print("=== 1. FIXING JOBS.JSON CORRUPTION ===")
with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

# Line 4851 had an unescaped newline in a string literal:
# "progress_msg": "Lỗi xử lý: yt-dlp tải video thất bại: WARNING: [youtube] No title found in player responses; falling \n
# let's repair any broken unescaped newlines inside strings or replace the malformed progress_msg
# Let's fix line 4851 specifically
fixed_text = re.sub(
    r'"progress_msg":\s*"([^"]*?)\r?\n\s*\},',
    r'"progress_msg": "\1"\n  },',
    text
)

# Test parsing
try:
    jobs_data = json.loads(fixed_text, strict=False)
    print(f"Fixed with regex! Loaded {len(jobs_data)} jobs.")
    with open(r'D:\Highlight_Video_Studio\jobs.json', 'w', encoding='utf-8') as f:
        json.dump(jobs_data, f, ensure_ascii=False, indent=2)
    print("Saved repaired jobs.json!")
except Exception as e:
    print("Regex fix didn't fully resolve, trying manual line parse:", e)
    # Let's do line by line inspection
    lines = text.splitlines()
    new_lines = []
    in_string = False
    for i, line in enumerate(lines):
        if 'Lỗi xử lý: yt-dlp' in line and not line.strip().endswith('"') and not line.strip().endswith('",'):
            # Close the quote
            line = line.rstrip() + '"'
        new_lines.append(line)
    try:
        jobs_data = json.loads("\n".join(new_lines), strict=False)
        print(f"Line fix success! Loaded {len(jobs_data)} jobs.")
        with open(r'D:\Highlight_Video_Studio\jobs.json', 'w', encoding='utf-8') as f:
            json.dump(jobs_data, f, ensure_ascii=False, indent=2)
        print("Saved repaired jobs.json via line fix!")
    except Exception as e2:
        print("Line fix failed:", e2)

print("\n=== 2. CHECK JOBS LOADING VIA APP.PY LOGIC ===")
try:
    with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8') as f:
        j = json.load(f)
    print(f"jobs.json currently has {len(j)} jobs.")
    # Show status breakdown
    statuses = {}
    for item in j:
        st = item.get("status", "unknown")
        statuses[st] = statuses.get(st, 0) + 1
    print("Jobs status breakdown:", statuses)
except Exception as e:
    print("Check error:", e)

