import requests
from bs4 import BeautifulSoup

r = requests.get("http://127.0.0.1:5080/")
print("Status code:", r.status_code)
html = r.text

print("Has 'pages-per-token-input':", 'id="pages-per-token-input"' in html)
print("Has 'Xem Reel Facebook':", 'Xem Reel Facebook' in html)
print("Has 'rebalanceTokenPageAllocation':", 'rebalanceTokenPageAllocation' in html)
