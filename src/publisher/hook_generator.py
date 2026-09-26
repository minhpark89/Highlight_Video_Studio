import requests
import json
import base64
import os
import re
import logging
from pathlib import Path

logger = logging.getLogger("hook_generator")

HVS_DIR = Path(r"D:\Highlight_Video_Studio")

def get_llm_config():
    try:
        with open(HVS_DIR / "config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg.get("llm", {})
    except Exception:
        return {
            "api_base": "http://100.89.167.97:8317/v1",
            "api_key": "***",
            "model": "gemini-3.1-flash-image"
        }

def generate_ai_hook_thumbnail(video_title: str, output_path: str = None) -> str:
    """
    Tạo ảnh Hook Thumbnail đỉnh cao bằng AI LLM (gemini-3.1-flash-image)
    chuẩn phong cách giật gân, tò mò tột đỉnh như mẫu boss gửi:
    - Text 3D đỏ/trắng cực to: WILDEST MOMENTS / SHOCKING TAKEDOWNS / CRAZY REVELATION
    - Banner vàng nổi bật: You Won't Believe This
    - Vòng tròn đỏ neon khoanh chi tiết kịch tính
    - Mũi tên đỏ chỉ thẳng vào vòng tròn
    - Icon camera REC góc trên
    """
    clean_title = re.sub(r'^(job_\d+_[a-f0-9]+_|clip_\d+_)', '', video_title, flags=re.IGNORECASE)
    clean_title = clean_title.replace('_', ' ').strip().title()

    llm_cfg = get_llm_config()
    api_base = llm_cfg.get("api_base", "http://100.89.167.97:8317/v1")
    api_key = ***"api_key", "")
    
    prompt = f"""Create a viral, high-CTR YouTube thumbnail and article hook image for a dramatic video about: "{clean_title}".
Style and visual elements:
- Ultra-realistic, cinematic night action scene with intense red and blue emergency/dramatic lighting, cinematic atmosphere.
- In the top half, huge bold 3D sensational text banner in thick condensed red letters with white outline: 'WILDEST MOMENTS!' or 'SHOCKING TAKEDOWN!'
- A bright yellow rectangular banner directly underneath saying 'You Won't Believe This' in bold black font.
- A glowing bright red circular outline highlighting the most intense action detail / subject on the ground.
- A bold curved red arrow pointing directly at the red circle.
- In the top-left corner, a camera overlay icon reading '● REC BODYCAM' with viewfinder brackets.
- Professional viral clickbait thumbnail style, 16:9 widescreen format, photorealistic, 8k resolution."""

    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gemini-3.1-flash-image",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    if not output_path:
        temp_dir = HVS_DIR / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(temp_dir / f"ai_hook_{abs(hash(clean_title)) % 100000}.jpg")

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            res_json = resp.json()
            choices = res_json.get("choices", [])
            if choices and choices[0].get("message", {}).get("images"):
                img_url = choices[0]["message"]["images"][0]["image_url"]["url"]
                if "base64," in img_url:
                    raw_b64 = img_url.split("base64,")[1]
                    raw_bytes = base64.b64decode(raw_b64)
                    with open(output_path, "wb") as f:
                        f.write(raw_bytes)
                    logger.info(f"AI Hook Image generated successfully: {output_path}")
                    return output_path
    except Exception as exc:
        logger.warning(f"Error generating AI hook image: {exc}")

    return ""
