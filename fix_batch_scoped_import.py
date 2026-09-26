from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's inspect api_distribute_batch definition
pos = text.find("def api_distribute_batch():")
end_pos = text.find("\n@app.route", pos)

func_code = text[pos:end_pos]
# Add import re inside api_distribute_batch directly to guarantee it has re
new_func_code = func_code.replace("def api_distribute_batch():\n", "def api_distribute_batch():\n    import re\n    from datetime import datetime, timedelta\n", 1)

text = text[:pos] + new_func_code + text[end_pos:]
app_path.write_text(text, encoding="utf-8")
print("Added explicit scoped imports into api_distribute_batch!")
