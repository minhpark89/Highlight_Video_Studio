import json
import re

print("=== 1. INSPECT JOBS.JSON CORRUPTION ===")
try:
    with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8') as f:
        content = f.read()
    print("Length of jobs.json:", len(content))
    try:
        data = json.loads(content)
        print("jobs.json is valid JSON! Count:", len(data))
    except Exception as e:
        print("jobs.json JSON ERROR:", e)
        # Try with strict=False
        try:
            data = json.loads(content, strict=False)
            print("With strict=False: SUCCESS! Count:", len(data))
            # Save repaired back
            with open(r'D:\Highlight_Video_Studio\jobs.json.bak', 'w', encoding='utf-8') as f_bak:
                f_bak.write(content)
            with open(r'D:\Highlight_Video_Studio\jobs.json', 'w', encoding='utf-8') as f_out:
                json.dump(data, f_out, ensure_ascii=False, indent=2)
            print("Successfully repaired and saved jobs.json!")
        except Exception as e2:
            print("strict=False also failed:", e2)
except Exception as fe:
    print("Cannot read jobs.json:", fe)

print("\n=== 2. INSPECT PAGES.JSON & TOKENS_VAULT.JSON ===")
try:
    with open(r'D:\Highlight_Video_Studio\pages.json', 'r', encoding='utf-8') as f:
        pages = json.load(f)
    print("pages.json count:", len(pages))
    if pages:
        print("Sample page item:", json.dumps(pages[0], ensure_ascii=False))
except Exception as e:
    print("pages.json error:", e)

try:
    with open(r'D:\Highlight_Video_Studio\tokens_vault.json', 'r', encoding='utf-8') as f:
        tokens = json.load(f)
    print("tokens_vault.json count:", len(tokens))
except Exception as e:
    print("tokens_vault.json error:", e)

