from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
content = app_py.read_text(encoding="utf-8")

# Let's inspect where api_distribute_batch is
pos_start = content.find('def api_distribute_batch():')
pos_next_route = content.find('@app.route', pos_start + 10)
print(f"api_distribute_batch span: {pos_start} to {pos_next_route}")
print("Lines around start:")
print(content[pos_start:pos_start+600])
print("\nLines around end:")
print(content[pos_next_route-300:pos_next_route])
