import subprocess

out = subprocess.check_output([
    "powershell", "-Command",
    "python -c \"import json; print('jobs:', len(json.load(open('D:/Highlight_Video_Studio/jobs.json', encoding='utf-8')))); print('tokens:', len(json.load(open('D:/Highlight_Video_Studio/tokens_vault.json', encoding='utf-8')))); print('pages:', len(json.load(open('D:/Highlight_Video_Studio/pages.json', encoding='utf-8'))))\""
], text=True)
print(out)
