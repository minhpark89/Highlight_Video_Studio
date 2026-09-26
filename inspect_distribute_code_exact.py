from pathlib import Path

txt = Path(r"D:\Highlight_Video_Studio\web\app.py").read_text(encoding="utf-8")
pos = txt.find("def api_distribute_batch")
pos_end = txt.find("def handle_schedule_rules", pos)
print("=== CURRENT api_distribute_batch ===")
print(txt[pos:pos_end])
