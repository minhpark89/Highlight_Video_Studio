with open(r'D:\Highlight_Video_Studio\web\app.py', 'r', encoding='utf-8') as f:
    app_text = f.read()

import re
# Check api_add_token implementation
m = re.search(r'def api_add_token\(\):.*?(?=@app\.route|\Z)', app_text, re.DOTALL)
if m:
    print("=== api_add_token ===")
    print(m.group(0))

# Check api_pages
m = re.search(r'def api_pages\(\):.*?(?=@app\.route|\Z)', app_text, re.DOTALL)
if m:
    print("=== api_pages ===")
    print(m.group(0))

