import time
import requests
from flask import request, jsonify
from web.app import app, load_config

@app.route("/api/llm/test", methods=["POST"])
def api_llm_test():
    data = request.json or {}
    api_base = data.get("api_base", "").strip()
    api_key = data.get("api_key", "").strip()
    model = data.get("model", "gemini-3-flash").strip()

    if not api_base:
        cfg = load_config()
        api_base = cfg.get("llm", {}).get("api_base", "")
        if not api_key:
            api_key = cfg.get("llm", {}).get("api_key", "")
        if not model or model == "gemini-3-flash":
            model = cfg.get("llm", {}).get("model", "gemini-3-flash")

    if not api_base:
        return jsonify({"success": False, "error": "Chưa điền LLM Provider Endpoint!"}), 400

    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Ping test. Reply with: PONG"}],
        "max_tokens": 15,
        "temperature": 0.1
    }
    try:
        t0 = time.time()
        resp = requests.post(url, headers=headers, json=payload, timeout=12)
        elapsed = round(time.time() - t0, 2)
        if resp.status_code == 200:
            res_json = resp.json()
            reply = res_json.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            return jsonify({
                "success": True,
                "elapsed": elapsed,
                "reply": reply,
                "message": f"Kết nối LLM thành công ({elapsed}s)! Phản hồi: '{reply}'"
            })
        else:
            err_detail = resp.text[:250]
            return jsonify({
                "success": False,
                "status_code": resp.status_code,
                "error": f"Lỗi HTTP {resp.status_code}: {err_detail}"
            }), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Không thể kết nối đến LLM Endpoint ({api_base}): {str(e)}"}), 500
