import json
import re

# 1. Check jobs.json parse error
with open(r'D:\Highlight_Video_Studio\jobs.json', 'rb') as f:
    raw = f.read()

print("Raw jobs.json size:", len(raw))

# Let's inspect where it fails
s = raw.decode('utf-8', errors='replace')
pos = 206756
print("Around 206756:")
print(repr(s[pos-50:pos+50]))

# Search for the character at 206756
print("Char at 206756:", repr(s[pos]))

