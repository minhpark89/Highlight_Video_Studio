from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# 1. Fix groups.forEach is not a function in loadLoHaGroups
old_code = """      const [resG, resC] = await Promise.all([
        fetch('/api/groups'),
        fetch('/api/clips')
      ]);
      const groups = await resG.json();
      const clipsData = await resC.json();
      const clips = Array.isArray(clipsData) ? clipsData : (clipsData.clips || []);"""

new_code = """      const [resG, resC] = await Promise.all([
        fetch('/api/groups'),
        fetch('/api/clips')
      ]);
      const groupsData = await resG.json();
      const groups = Array.isArray(groupsData) ? groupsData : (groupsData.groups || []);
      const clipsData = await resC.json();
      const clips = Array.isArray(clipsData) ? clipsData : (clipsData.clips || []);"""

if old_code in html:
    html = html.replace(old_code, new_code, 1)
    print("Fixed loadLoHaGroups groups parsing!")
else:
    print("old_code not found for groups parsing, checking alternatives")

# 2. Clean up sidebar labels (remove hardcoded numbers)
html = html.replace("<span>Quản lý 100 Fanpage</span>", "<span>Quản lý Page</span>")
html = html.replace("<span>Quản lý Token (31 Token)</span>", "<span>Quản lý Token</span>")

index_path.write_text(html, encoding="utf-8")
print("Saved index.html!")
