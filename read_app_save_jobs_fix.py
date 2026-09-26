with open(r'D:\Highlight_Video_Studio\web\app.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
m_load = re.search(r'def load_jobs\(\):.*?(?=def |\Z)', text, re.DOTALL)
if m_load:
    print("=== load_jobs in app.py ===")
    print(m_load.group(0))

m_save = re.search(r'def save_jobs\([^)]*\):.*?(?=def |\Z)', text, re.DOTALL)
if m_save:
    print("=== save_jobs in app.py ===")
    print(m_save.group(0))

