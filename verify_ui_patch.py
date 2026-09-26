from pathlib import Path

tmpl_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
web_path = Path(r"D:\Highlight_Video_Studio\web\index.html")

tmpl_text = tmpl_path.read_text(encoding="utf-8")
web_text = web_path.read_text(encoding="utf-8")

print("Checking tmpl_text:")
print("- sched-conf-use-llm:", "sched-conf-use-llm" in tmpl_text)
print("- use_llm_comment:", "use_llm_comment" in tmpl_text)

print("\nChecking web_text:")
print("- sched-conf-use-llm:", "sched-conf-use-llm" in web_text)
print("- use_llm_comment:", "use_llm_comment" in web_text)
