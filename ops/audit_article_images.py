from __future__ import annotations

import argparse
import concurrent.futures
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from PIL import ImageFile


class ArticleImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attributes):
        values = dict(attributes)
        if tag == "img" and values.get("src"):
            self.images.append(values["src"])
        if tag == "meta" and values.get("property") == "og:image" and values.get("content"):
            self.images.append(values["content"])


def public_url(value):
    parts = urlsplit(value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def image_dimensions(url):
    parser = ImageFile.Parser()
    with requests.get(url, timeout=12, stream=True, headers={"Range": "bytes=0-262143"}) as response:
        response.raise_for_status()
        received = 0
        for chunk in response.iter_content(4096):
            parser.feed(chunk)
            received += len(chunk)
            if parser.image:
                return parser.image.size
            if received >= 262144:
                break
    raise ValueError("Image dimensions were not readable within the bounded response.")


def article_image_urls(article_url, source):
    parser = ArticleImageParser()
    start = source.find("Original video summary")
    end = source.find("Full Uncut Footage", start) if start >= 0 else -1
    parser.feed(source[start:end] if start >= 0 and end > start else source)
    return list(dict.fromkeys(urljoin(article_url, image) for image in parser.images
                              if urlsplit(urljoin(article_url, image)).scheme in ("http", "https")))


def inspect_article(article_url):
    result = {"article_url": public_url(article_url), "images": [], "read_only": True}
    try:
        response = requests.get(article_url, timeout=15)
        response.raise_for_status()
        for image_url in article_image_urls(article_url, response.text):
            image = {"url": public_url(image_url)}
            try:
                width, height = image_dimensions(image_url)
                image.update({"width": width, "height": height, "landscape": width / max(1, height) >= 1.45})
            except Exception as exc:
                image["error_type"] = type(exc).__name__
            result["images"].append(image)
        result["needs_review"] = len(result["images"]) < 3 or any(not image.get("landscape") for image in result["images"])
    except Exception as exc:
        result.update({"error_type": type(exc).__name__, "needs_review": True})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("posts", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    posts = json.loads(args.posts.read_text(encoding="utf-8"))
    urls = sorted({str(post.get("article_url") or "").strip() for post in posts if post.get("article_url")})
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        articles = list(executor.map(inspect_article, urls))
    report = {"read_only": True, "articles_checked": len(articles),
              "needs_review": sum(article["needs_review"] for article in articles), "articles": articles}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "articles"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
