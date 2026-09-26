import urllib.request
import json

res = urllib.request.urlopen("http://127.0.0.1:5080/api/clips")
data = json.loads(res.read().decode())
clips = data.get("clips", [])
print(f"Total clips in /api/clips: {len(clips)}")
if clips:
    print("Sample clip:", clips[0])
