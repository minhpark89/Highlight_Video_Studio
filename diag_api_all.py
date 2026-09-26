import requests

try:
    print("/api/jobs:", requests.get("http://127.0.0.1:5080/api/jobs").json())
except Exception as e:
    print("/api/jobs error:", e)

try:
    print("/api/clips:", requests.get("http://127.0.0.1:5080/api/clips").json())
except Exception as e:
    print("/api/clips error:", e)

try:
    print("/api/system/youtube_status:", requests.get("http://127.0.0.1:5080/api/system/youtube_status").json())
except Exception as e:
    print("youtube_status error:", e)
