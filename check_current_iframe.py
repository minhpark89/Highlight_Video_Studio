import requests

url = "https://bestnews.cfx.bz/blog/clip-2-74274"
r = requests.get(url, verify=False)
print("Status:", r.status_code)
# Search for youtube iframe in clip-2-74274
import re
print("Iframe in page:", re.findall(r'<iframe[^>]*src="([^"]+)"', r.text))
