import requests
import json

base_url = "https://bestnews.cfx.bz"
print("Checking bestnews.cfx.bz...")

# 1. Login session
s = requests.Session()
s.verify = False

r_login_page = s.get(f"{base_url}/login")
print("Login page status:", r_login_page.status_code)
# find csrf token
import re
m = re.search(r'name="_token" value="([^"]+)"', r_login_page.text)
token = m.group(1) if m else ""
print("CSRF Token:", token)

# Try login
login_data = {
    "_token": token,
    "email": "admin@example.com", # let's check what username/email is accepted
    "username": "admin",
    "password": "admin123"
}
# Let's check what input fields exist in login page
inputs = re.findall(r'<input[^>]+name="([^"]+)"[^>]*>', r_login_page.text)
print("Login inputs:", inputs)

r_post = s.post(f"{base_url}/login", data={"_token": token, "email": "admin", "password": "admin123"}, allow_redirects=True)
print("Login result URL:", r_post.url, "Status:", r_post.status_code)
if "backend" in r_post.url or "dashboard" in r_post.url or "admin" in r_post.url:
    print("Login successful!")
else:
    print("Login response snippet:", r_post.text[:300])
