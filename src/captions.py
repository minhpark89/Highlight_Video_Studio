"""Portable ASS presets and bounded clip-relative word timing."""
import math
import re
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parents[1] / "web/static/fonts"
STYLES = {
    "hormozi_yellow": {"font": "Be Vietnam Pro", "size": 82, "active": "&H0022FFFF&", "outline": 6, "upper": True},
    "clean_white": {"font": "Be Vietnam Pro", "size": 72, "active": "&H00FFFFFF&", "outline": 3, "upper": False},
    "karaoke_cyan": {"font": "Barlow Condensed", "size": 90, "active": "&H00FFFF00&", "outline": 5, "upper": True},
    "neon_green": {"font": "Barlow Condensed", "size": 90, "active": "&H0033FF00&", "outline": 5, "upper": True},
    "viral_anton": {"font": "Anton", "size": 88, "active": "&H0022FFFF&", "outline": 5, "upper": True},
    "viral_condensed": {"font": "Barlow Condensed", "size": 92, "active": "&H0080FF80&", "outline": 5, "upper": True},
    "viral_vietnam": {"font": "Be Vietnam Pro", "size": 80, "active": "&H00FF80FF&", "outline": 5, "upper": False},
}


def normalize_words(words, duration=None):
    result = []
    for item in words or []:
        try:
            text = str(item.get("word") or "").strip()
            start, end = float(item["start"]), float(item["end"])
            if not text or not math.isfinite(start) or not math.isfinite(end) or end <= 0:
                continue
            start = max(0, start)
            if duration is not None:
                end = min(float(duration), end)
            if end <= start:
                continue
            result.append({"word": text, "start": start, "end": end})
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    result.sort(key=lambda w: (w["start"], w["end"]))
    # Rolling YouTube caption windows can repeat words. Never let ASS dialogue
    # overlap: overlapping events would display competing chunks at once.
    clean = []
    for item in result:
        if clean and item["word"].casefold() == clean[-1]["word"].casefold() and abs(item["start"] - clean[-1]["start"]) < .04:
            continue
        if clean:
            clean[-1]["end"] = min(clean[-1]["end"], item["start"])
            if clean[-1]["end"] <= clean[-1]["start"]:
                clean.pop()
        clean.append(item)
    return clean


def ass_time(seconds):
    total = max(0, round(float(seconds) * 100))
    hours, rest = divmod(total, 360000)
    minutes, rest = divmod(rest, 6000)
    seconds, cs = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{cs:02d}"


def write_ass(words, path, style_name="hormozi_yellow", *, width=1080, height=1920):
    style = STYLES.get(style_name, STYLES["hormozi_yellow"])
    size = round(style["size"] * width / 1080)
    margin = round(height * .155)
    white = "&H00FFFFFF&"
    header = f"""[Script Info]
Title: Highlight Video Karaoke
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['font']},{size},{white},{white},&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,{style['outline']},2,2,60,60,{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    chunks, chunk = [], []
    for word in normalize_words(words):
        text = re.sub(r"[{}\\]", "", word["word"])
        text = text.upper() if style["upper"] else text
        if chunk and (len(chunk) >= 3 or sum(len(w["word"]) + 1 for w in chunk) + len(text) > 24
                      or word["start"] - chunk[-1]["end"] > .65):
            chunks.append(chunk)
            chunk = []
        chunk.append({**word, "word": text})
    if chunk:
        chunks.append(chunk)
    lines = []
    for chunk in chunks:
        for active, word in enumerate(chunk):
            start, end = ass_time(word["start"]), ass_time(word["end"])
            if start == end:
                continue
            parts = [r"{\c" + (style["active"] if i == active else white) + "}" + w["word"] for i, w in enumerate(chunk)]
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,," + " ".join(parts))
    Path(path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    return path
