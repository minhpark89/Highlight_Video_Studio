"""Inspect CMS editorial HTML without relying on generated heading labels."""
import html
import re


def article_quality(source, *, minimum_words=600, minimum_images=3, expected_images=None):
    from core.website_article_service import WebsiteServiceError
    article = re.search(r"<article\b[^>]*>(.*?)</article>", source, re.S | re.I)
    if article:
        source = article.group(1)
    source = re.sub(r"<(script|style|nav|aside|footer|header)\b[^>]*>.*?</\1\s*>", "", source, flags=re.S | re.I)
    prose = bool(re.search(r"<p\b|original-video-summary", source, re.I))
    video = bool(re.search(r"<(?:iframe|video)\b", source, re.I))
    if not prose or not video:
        raise WebsiteServiceError("Bài public thiếu nội dung tóm tắt hoặc phần nhúng video gốc")
    images = [html.unescape(url) for url in re.findall(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\']', source, re.I)]
    image_count = len(set(images))
    words = len(re.findall(r"\b[A-Za-z]+\b", html.unescape(re.sub(r"<[^>]+>", " ", source))))
    if expected_images and any(html.unescape(image) not in images for image in expected_images):
        raise WebsiteServiceError("Bài public thiếu một hoặc nhiều ảnh minh họa đã gửi")
    if image_count < minimum_images:
        raise WebsiteServiceError(f"Bài public chỉ có {image_count} ảnh, cần {minimum_images}")
    if words < minimum_words:
        raise WebsiteServiceError(f"Bài public chỉ có {words} từ, cần {minimum_words}")
    return {"success": True, "word_count": words, "image_count": image_count}
