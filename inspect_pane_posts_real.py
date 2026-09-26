from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# 1. Look for Quản lý Bài Đăng header to add "Hủy bài đang hẹn" (Clear scheduled posts) and "Xóa toàn bộ bài đăng"
# Let's inspect pane-posts
pos_posts = html.find('id="pane-posts"')
pos_table = html.find('<table', pos_posts)

print("Pane-posts top section:\n", html[pos_posts:pos_table])
