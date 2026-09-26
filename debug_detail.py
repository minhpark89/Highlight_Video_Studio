with open(r'D:\Highlight_Video_Studio\jobs.json', 'rb') as f:
    raw = f.read()

pos = 206756
start = max(0, pos - 150)
end = min(len(raw), pos + 150)
print("RAW BYTES AROUND 206756:")
print(raw[start:end])
print("\nDECODED STRING:")
try:
    print(raw[start:end].decode('utf-8', errors='replace'))
except Exception as e:
    print("Decode err:", e)
