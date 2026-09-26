from pathlib import Path

# Check where reel_poster is located
for p in Path(r"D:\Highlight_Video_Studio").glob("**/*poster*.py"):
    print("Found:", p)

for p in Path(r"D:\Highlight_Video_Studio").glob("**/*publish*.py"):
    print("Found publish:", p)
