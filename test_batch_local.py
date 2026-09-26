import sys
sys.path.insert(0, r"D:\Highlight_Video_Studio")
sys.path.insert(0, r"D:\Highlight_Video_Studio\web")

from web.app import app

client = app.test_client()
res = client.post('/api/distribute/batch', json={
    "group_id": "group_bm1",
    "stagger_minutes": 15,
    "auto_first_comment": True,
    "delete_after_schedule": False
})
print("Status code:", res.status_code)
if res.status_code != 200:
    print("Data:", res.data.decode('utf-8')[:1000])
else:
    print("Success! Scheduled count:", res.get_json().get("scheduled_count"))
