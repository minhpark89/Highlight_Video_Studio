with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

import re
# check loadJobsTable
m = re.search(r'async function loadJobsTable\(.*?\n  \}', text, re.DOTALL)
if m:
    print("=== loadJobsTable ===")
    print(m.group(0)[:1500])

