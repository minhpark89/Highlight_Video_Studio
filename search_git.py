import subprocess

try:
    res = subprocess.run(["git", "log", "-S", "loadWebsiteConfig", "-p", "-n", "3"], cwd="D:/Highlight_Video_Studio", capture_output=True, text=True)
    print("Git log:")
    print(res.stdout[:2000])
except Exception as e:
    print(e)
