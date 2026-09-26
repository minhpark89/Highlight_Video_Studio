import sys
import traceback
from pathlib import Path

# Add D:\Highlight_Video_Studio to sys.path
sys.path.insert(0, r"D:\Highlight_Video_Studio")
sys.path.insert(0, r"D:\Highlight_Video_Studio\web")

try:
    from web.app import app
    client = app.test_client()
    res = client.post('/api/distribute/batch', json={
        "group_id": "group_bm1",
        "stagger_minutes": 15,
        "auto_first_comment": True,
        "delete_after_schedule": False
    })
    print("Response status:", res.status_code)
    print("Response data:", res.get_json() if res.is_json else res.data.decode('utf-8'))
except Exception as e:
    traceback.print_exc()
