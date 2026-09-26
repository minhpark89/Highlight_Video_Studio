with open(r'D:\Highlight_Video_Studio\jobs.json', 'rb') as f:
    raw = f.read()

print("File size on disk:", len(raw))
# decode
try:
    text = raw.decode('utf-8')
    import json
    data = json.loads(text)
    print("SUCCESS LOAD JSON: len =", len(data))
    if data:
        print("First job ID:", data[0].get("id"), "status:", data[0].get("status"))
except Exception as e:
    print("FAILED LOAD JSON:", e)

