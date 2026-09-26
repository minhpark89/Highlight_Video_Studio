import re

with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect pane-pages to see how groups are currently rendered or if there is already a table for posts
print("Has loadPosts:", 'loadPosts' in text)
print("Has loadGroups:", 'loadGroups' in text)
print("Has renderPages:", 'renderPages' in text)

# Let's check occurrences of /api/posts
matches = [m.start() for m in re.finditer(r'/api/posts', text)]
print("Matches for /api/posts in index.html:", len(matches))
for idx in matches[:5]:
    print(text[idx-50:idx+100])
    print("---")
