import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

url = "https://bestnews.cfx.bz/blog/thrilling-sports-highlight-uncut-play-2026"
r = requests.get(url, verify=False)
soup = BeautifulSoup(r.text, "html.parser")
body = soup.find("div", class_="module-article-content__body")
print("Status:", r.status_code)
print("Contains video tag?", "<video" in str(body))
print("Body snippet:\n", str(body)[:1500])
