import requests

res = requests.post("http://127.0.0.1:5080/api/distribute/batch", json={
    "group_id": "group_bm1",
    "stagger_minutes": 15,
    "auto_first_comment": True,
    "delete_after_schedule": False
})
print("Status:", res.status_code)
print("Text:", res.text[:2000])
