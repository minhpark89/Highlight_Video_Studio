from pathlib import Path

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
content = app_py.read_text(encoding="utf-8")

old_rules = """@app.route("/api/schedule/rules", methods=["GET", "POST"])
def handle_schedule_rules():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        saved = save_schedule_rules(data)
        return jsonify({"status": "ok", "rules": saved})
    return jsonify({"status": "ok", "rules": get_schedule_rules()})"""

new_rules = """SCHEDULE_RULES_FILE = BASE_DIR / "config" / "schedule_rules.json"

def get_schedule_rules():
    if not SCHEDULE_RULES_FILE.exists():
        return {
            "slots": ["07:00", "11:30", "17:00", "20:00"],
            "stagger_minutes": 15,
            "posts_per_day": 4,
            "auto_first_comment": True
        }
    try:
        import json
        return json.loads(SCHEDULE_RULES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {
            "slots": ["07:00", "11:30", "17:00", "20:00"],
            "stagger_minutes": 15,
            "posts_per_day": 4,
            "auto_first_comment": True
        }

def save_schedule_rules(rules):
    try:
        import json
        SCHEDULE_RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULE_RULES_FILE.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")
        return rules
    except Exception:
        return rules

@app.route("/api/schedule/rules", methods=["GET", "POST"])
def handle_schedule_rules():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        saved = save_schedule_rules(data)
        return jsonify({"status": "ok", "rules": saved})
    return jsonify({"status": "ok", "rules": get_schedule_rules()})"""

if old_rules in content:
    content = content.replace(old_rules, new_rules)
    app_py.write_text(content, encoding="utf-8")
    print("Fixed get_schedule_rules and save_schedule_rules in app.py!")
else:
    print("Could not find exact old_rules in app.py")
