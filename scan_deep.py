import re

with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# In research results, what does clicking "Ném vào Render" on a card do?
# Let's inspect sendToRender function and where it is called
print("=== sendToRender calls ===")
for m in re.finditer(r'sendToRender\([^)]*\)', text):
    start = max(0, m.start() - 100)
    end = min(len(text), m.end() + 100)
    print(text[start:end].replace('\n', ' '))

print("\n=== sendSelectedToStudio calls ===")
for m in re.finditer(r'sendSelectedToStudio\([^)]*\)', text):
    start = max(0, m.start() - 100)
    end = min(len(text), m.end() + 100)
    print(text[start:end].replace('\n', ' '))

