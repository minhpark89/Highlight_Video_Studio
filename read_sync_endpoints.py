with open(r'D:\Highlight_Video_Studio\web\app.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
m_add = re.search(r'def api_add_token\(\):.*?(?=@app\.route|\Z)', text, re.DOTALL)
if m_add:
    print("=== api_add_token ===")
    print(m_add.group(0)[:1500])

