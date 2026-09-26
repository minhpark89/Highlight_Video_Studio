import requests
from pathlib import Path

r = requests.get("http://127.0.0.1:5080/api/pages")
print("API /api/pages status:", r.status_code)
pages_data = r.json()
print("API /api/pages length:", len(pages_data.get("pages", [])))
