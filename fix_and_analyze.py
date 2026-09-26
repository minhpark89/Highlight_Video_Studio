import json

print("--- 1. Analyzing jobs.json corruption ---")
with open(r'D:\Highlight_Video_Studio\jobs.json', 'rb') as f:
    raw = f.read()

# Let's locate why json.loads fails
try:
    data = json.loads(raw.decode('utf-8'))
    print("Direct loads: SUCCESS, count =", len(data))
except Exception as e:
    print("Direct loads failed:", e)

# Test decoding char by char or finding invalid chars
s = raw.decode('utf-8', errors='replace')
try:
    # Try finding invalid control chars
    import re
    # Clean control characters inside string literals that are not \n, \r, \t
    # or invalid unescaped control chars
    data = json.loads(s, strict=False)
    print("strict=False: SUCCESS, count =", len(data))
except Exception as e:
    print("strict=False failed:", e)
    # Let's find exactly which line/col
    import traceback
    traceback.print_exc()

