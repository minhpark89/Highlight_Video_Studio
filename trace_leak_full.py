import os
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("Hỗ trợ Hashtags")
print("Position:", pos)
if pos != -1:
    # Print 1500 chars before and 1500 chars after
    start = max(0, pos - 1500)
    end = min(len(text), pos + 1500)
    with open(BASE_DIR / "leaked_full_trace.txt", "w", encoding="utf-8") as f_out:
        f_out.write(text[start:end])
    print(f"Written to leaked_full_trace.txt from {start} to {end}")
    
    # Also find what tag opens before start
    print("--- 500 chars before ---")
    print(text[pos-500:pos])
    print("--- 500 chars after ---")
    print(text[pos:pos+500])
