import requests
from web.app import app

with app.test_client() as client:
    res = client.get("/api/schedule/rules")
    print("Test client /api/schedule/rules:", res.status_code)
    print(res.data)
