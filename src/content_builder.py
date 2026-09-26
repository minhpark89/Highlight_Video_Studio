import os
import re
import json
import time
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "output"

def get_llm_candidates():
    cfg_file = BASE_DIR / "config.json"
    cfg = {}
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass
    llm = cfg.get("llm", {})
    configured_base = llm.get("api_base", "http://100.89.167.97:8317/v1")
    api_key = llm.get("api_key", "oc_clip_904296c3e5356d9027135dd4a881d9e102bbe4c420d1d4a9ab7b133d27d548b1")
    model = llm.get("model", "gemini-3-flash")

    # Danh sách các endpoint 9router ứng viên để auto-detect trên các máy khác nhau
    raw_candidates = [
        configured_base,
        "http://127.0.0.1:8317/v1",
        "http://localhost:8317/v1",
        "http://100.89.167.97:8317/v1",
        "http://100.83.61.102:8317/v1",
        "http://192.168.1.3:8317/v1"
    ]
    seen = set()
    endpoints = []
    for c in raw_candidates:
        if c and c not in seen:
            seen.add(c)
            endpoints.append(c)

    return {
        "endpoints": endpoints,
        "api_key": api_key,
        "model": model,
        "configured_base": configured_base
    }

def test_and_pick_active_llm():
    """Tự động kiểm tra và bắt lấy endpoint 9router đang hoạt động trên máy này hoặc máy khác"""
    data = get_llm_candidates()
    headers = {"Authorization": f"Bearer {data['api_key']}"}
    
    for ep in data["endpoints"]:
        try:
            r = requests.get(f"{ep}/models", headers=headers, timeout=1.8)
            if r.status_code == 200:
                return {
                    "api_base": ep,
                    "api_key": data["api_key"],
                    "model": data["model"],
                    "status": "connected"
                }
        except Exception:
            continue

    return {
        "api_base": data["configured_base"],
        "api_key": data["api_key"],
        "model": data["model"],
        "status": "fallback"
    }

def generate_viral_content(title: str, summary: str = "", hook: str = "", video_url: str = ""):
    """
    Sử dụng LLM 9router viết bài đăng Facebook cực hay, tiêu đề viral,
    và đặc biệt FIRST COMMENT dạng gây tò mò tột độ (Curiosity Gap).
    """
    llm = test_and_pick_active_llm()
    prompt = f"""Bạn là một chuyên gia sáng tạo nội dung viral mạng xã hội (Facebook Reels, TikTok, YouTube Shorts), am hiểu tâm lý tò mò tương tự phong cách Longform Studio.

Nhiệm vụ: Dựa vào tiêu đề và nội dung video sau:
1. TIÊU ĐỀ VIRAL (Hook title): Cực kỳ giật gân, khơi gợi tò mò, viết HOA hoặc kèm emoji gây sốc.
2. BÀI ĐĂNG FACEBOOK HOÀN CHỈNH:
   - 3 giây đầu: Câu Hook đánh thẳng vào tâm lý tò mò.
   - Thân bài: Ngắn gọn, kịch tính, dùng bullet emoji thoáng mắt.
   - Kết bài: Kêu gọi hành động (CTA) kích thích tranh luận và chia sẻ.
   - Kèm 5-6 hashtags thịnh hành.
3. FIRST COMMENT (Bình luận đầu tiên ghim top):
   - VIẾT DẠNG CỰC KỲ GÂY TÒ MÒ (Curiosity Gap).
   - Tuyệt đối không tiết lộ đáp án/kết cục, mà hé lộ 1 chi tiết bất thường, bí ẩn hoặc sốc nhất khiến bất kỳ ai đọc xong cũng phải bấm vào xem kỹ lại video hoặc vào tranh cãi ngay lập tức (Ví dụ: 'Mọi người để ý kỹ ở giây thứ 35, hành động bất thường của...', 'Cái kết ở phút cuối ai xem rồi mới hiểu sự thật...', 'Có một chi tiết ít ai để ý nhưng giải thích tất cả...').

Thông tin video:
- Tiêu đề gốc: {title}
- Tóm tắt / Hook: {hook or summary or "Tình huống kịch tính, bất ngờ"}
- Link gốc: {video_url}

ĐỊNH DẠNG TRẢ VỀ: DUY NHẤT 1 JSON (không bọc giải thích):
{{
  "viral_title": "...",
  "facebook_post": "...",
  "first_comment": "...",
  "hashtags": ["#viral", "#shorts", "#xuhuong"]
}}
"""
    headers = {
        "Authorization": f"Bearer {llm['api_key']}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": llm["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.45
    }

    try:
        r = requests.post(f"{llm['api_base']}/chat/completions", json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            res_json = r.json()
            txt = res_json["choices"][0]["message"]["content"]
            m = re.search(r'\{[\s\S]*\}', txt)
            if m:
                return json.loads(m.group(0))
            return json.loads(txt)
    except Exception as e:
        print(f"[Content Generator Error]: {e}")

    # Fallback template chuyên nghiệp
    clean_title = title.strip()
    return {
        "viral_title": f"🚨 SỰ THẬT KHIẾN TẤT CẢ PHẢI SỐC: {clean_title.upper()}",
        "facebook_post": f"🔥 Tình huống căng thẳng ngoài sức tưởng tượng!\n\n💥 Chỉ một quyết định trong vài giây đã làm thay đổi toàn bộ sự việc. Ai có mặt tại hiện trường cũng không tin vào mắt mình.\n\n👇 Xem trọn vẹn diễn biến để hiểu rõ ngọn ngành câu chuyện!\n\n#viral #xuhuong #kichtinh #hot #shorts #trending",
        "first_comment": "👀 Mọi người để ý kỹ chi tiết lúc đối tượng vừa quay mặt lại ở nửa sau video... Hành động đó chứng minh điều gì? Ai nhận ra điểm bất thường chưa?",
        "hashtags": ["#viral", "#xuhuong", "#trending", "#kichtinh"]
    }

def render_stylish_thumbnail(video_path: str, output_path: str, banner_text: str = "", timestamp_sec: float = 2.5):
    """
    Tạo ảnh Thumbnail chuyên nghiệp phong cách Longform Studio:
    Trích xuất frame rõ nét từ video, phủ bóng mờ phân tầng, thêm chữ Title giật gân font Impact màu Vàng Neon viền Đen dày.
    """
    import subprocess

    NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
    temp_frame = TEMP_DIR / f"thumb_src_{int(time.time()*1000)}.jpg"
    try:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(max(0.5, timestamp_sec)),
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "2",
            str(temp_frame)
        ]
        subprocess.run(cmd, capture_output=True, timeout=30, creationflags=NO_WINDOW)
        if not temp_frame.exists():
            return None

        with Image.open(str(temp_frame)) as source:
            orig_w, orig_h = source.size
            if orig_h > orig_w:
                w, h = 1080, 1920
            else:
                w, h = 1280, 720

            img = ImageOps.fit(source.convert("RGB"), (w, h), method=Image.Resampling.LANCZOS)
            img = ImageEnhance.Contrast(img).enhance(1.12)
            img = ImageEnhance.Color(img).enhance(1.15)

            # Lớp bóng đổ tối cho phần trên để nổi bật banner chữ
            canvas = img.convert("RGBA")
            shade = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            sd = ImageDraw.Draw(shade)
            banner_h = int(h * 0.24)
            sd.rectangle((0, 0, w, banner_h), fill=(0, 0, 0, 195))
            sd.rectangle((0, h - int(banner_h * 0.7), w, h), fill=(0, 0, 0, 160))
            canvas = Image.alpha_composite(canvas, shade)

            draw = ImageDraw.Draw(canvas)
            font_path = "C:/Windows/Fonts/impact.ttf"
            if not os.path.exists(font_path):
                font_path = "C:/Windows/Fonts/arialbd.ttf"

            text = (banner_text or "CÚ TWIST KHÔNG THỂ NGỜ").strip().upper()
            if len(text) > 55:
                text = text[:52] + "..."

            font_size = int(w * 0.075)
            try:
                font = ImageFont.truetype(font_path, font_size)
            except Exception:
                font = ImageFont.load_default()

            words = text.split()
            lines = []
            cur = ""
            for word in words:
                trial = f"{cur} {word}".strip()
                bbox = draw.textbbox((0, 0), trial, font=font, stroke_width=4)
                if bbox[2] - bbox[0] > (w - 70):
                    if cur:
                        lines.append(cur)
                    cur = word
                else:
                    cur = trial
            if cur:
                lines.append(cur)
            lines = lines[:2]

            line_heights = [draw.textbbox((0, 0), l, font=font, stroke_width=4)[3] for l in lines]
            total_h = sum(line_heights) + (len(lines) - 1) * 8
            y_pos = (banner_h - total_h) // 2

            for i, l in enumerate(lines):
                bbox = draw.textbbox((0, 0), l, font=font, stroke_width=4)
                line_w = bbox[2] - bbox[0]
                x_pos = (w - line_w) // 2
                draw.text((x_pos, y_pos), l, font=font, fill="#FFE600", stroke_width=5, stroke_fill="#000000")
                y_pos += line_heights[i] + 8

            canvas.convert("RGB").save(str(output_path), quality=92, optimize=True)
            return str(output_path)
    except Exception as e:
        print(f"[Render stylish thumbnail error]: {e}")
        return None
    finally:
        if temp_frame.exists():
            try:
                temp_frame.unlink()
            except Exception:
                pass
