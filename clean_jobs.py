import json

with open(r'D:\Highlight_Video_Studio\jobs.json', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

# Find all JSON object array
# Let's decode properly
import re
# We know it starts with [ and ends with ]
m = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
if m:
    candidate = m.group(0)
    try:
        data = json.loads(candidate)
        print("Direct parsed array! Count:", len(data))
        with open(r'D:\Highlight_Video_Studio\jobs.json', 'w', encoding='utf-8') as out:
            json.dump(data, out, ensure_ascii=False, indent=2)
        print("Overwritten clean jobs.json!")
    except Exception as e:
        print("Regex match failed:", e)
        # Try raw decode
        decoder = json.JSONDecoder()
        try:
            obj, idx = decoder.raw_decode(text)
            print("raw_decode parsed! Count:", len(obj), "Ended at:", idx)
            with open(r'D:\Highlight_Video_Studio\jobs.json', 'w', encoding='utf-8') as out:
                json.dump(obj, out, ensure_ascii=False, indent=2)
            print("Successfully saved raw_decode result to jobs.json!")
        except Exception as e2:
            print("raw_decode failed:", e2)

