from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's check if website_publisher import is at the top of app.py
print("website_publisher in app.py:", "website_publisher" in text)

# Let's check api_distribute_batch
pos = text.find("def api_distribute_batch():")
pos_rules = text.find("SCHEDULE_RULES_FILE = BASE_DIR", pos)
print("api_distribute_batch lines:", len(text[pos:pos_rules].splitlines()))

# Let's check index.html
tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
tmpl_text = tmpl.read_text(encoding="utf-8")
print("sched-conf-use-llm in tmpl:", "sched-conf-use-llm" in tmpl_text)
print("use_llm_comment in tmpl:", "use_llm_comment" in tmpl_text)
