import requests
import json
import logging

logger = logging.getLogger("llm_curiosity")

def generate_curiosity_comment_with_llm(video_title: str, article_url: str, config: dict = None) -> str:
    """
    Sinh First Comment kích thích tò mò (Curiosity Gap) bằng tiếng Anh dẫn link web.
    Fallback về mẫu chuẩn nếu tắt LLM hoặc lỗi mạng.
    """
    fallback_comment = (
        f"🔥 Watch the full uncut footage and breakdown here: {article_url}\n"
        f"👉 Scroll down the article to stream the complete high-definition video!"
    )
    
    if not config:
        try:
            with open(r"D:\Highlight_Video_Studio\config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {}
            
    llm_cfg = config.get("llm", {})
    api_base = llm_cfg.get("api_base", "http://100.89.167.97:8317/v1")
    api_key = llm_cfg.get("api_key", "")
    model = llm_cfg.get("model", "gemini-3-flash")
    
    prompt = f"""You are a master social media growth hacker specializing in viral Facebook Reels and high-CTR curiosity gap hooks.
Write a single, highly engaging, curiosity-piquing First Comment in English for a video titled: "{video_title}".
Rules:
1. The comment must hook the audience's extreme curiosity about the full scene / outcome / backstory.
2. Must seamlessly include the link: {article_url}
3. End with a short CTA guiding them to scroll down the article to watch the complete footage.
4. Keep it under 280 characters, use 2-3 expressive emojis.
5. Return ONLY the final comment text. No explanations, no quotes."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You write viral, high-conversion curiosity comments for video highlights."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 120,
        "temperature": 0.8
    }

    try:
        url = f"{api_base.rstrip('/')}/chat/completions"
        resp = requests.post(url, headers=headers, json=payload, timeout=6)
        if resp.status_code == 200:
            res_json = resp.json()
            comment = res_json["choices"][0]["message"]["content"].strip()
            # Đảm bảo có chứa link article_url
            if article_url not in comment:
                comment += f"\n👉 Stream the full uncut video here: {article_url}"
            return comment
        else:
            logger.warning(f"LLM request returned status {resp.status_code}: {resp.text}")
    except Exception as exc:
        logger.warning(f"LLM curiosity generation failed: {exc}")

    return fallback_comment

if __name__ == "__main__":
    test_title = "Lionel Messi Insane Last Second Goal vs Real Madrid"
    test_link = "https://bestnews.cfx.bz/blog/messi-insane-goal"
    print("Testing LLM curiosity comment generation:")
    res = generate_curiosity_comment_with_llm(test_title, test_link)
    print("Result:\n", res)
