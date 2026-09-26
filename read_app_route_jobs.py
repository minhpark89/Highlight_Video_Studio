with open(r'D:\Highlight_Video_Studio\web\app.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
m = re.search(r'@app\.route\(["\']/api/jobs["\'].*?\n(?:def|\Z)', text, re.DOTALL)
if m:
    print("Match /api/jobs:")
    print(m.group(0))
else:
    # find where /api/jobs is defined
    idx = text.find('/api/jobs')
    print("Found /api/jobs at index:", idx)
    print(text[idx-50:idx+400])

