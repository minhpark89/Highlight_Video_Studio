import re

# Inspect index.html of Highlight Video Studio
with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Check what happens when clicking links or buttons in research results:
# Let's inspect the exact HTML generated in research-results-container
idx = html.find('container.innerHTML = results.map')
print(html[idx:idx+2000])

