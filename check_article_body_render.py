import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

url = "https://bestnews.cfx.bz/blog/epic-football-highlight-uncut-moments-2026"
r = requests.get(url, verify=False)
soup = BeautifulSoup(r.text, "html.parser")
body = soup.find("div", class_="module-article-content__body")
print("Full article body text/html in bestnews:")
print(str(body)[:2500])
