"""Shared article formatting for drafts and the public CMS body."""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from src.english_text import english_or_default

MIN_ARTICLE_WORDS = 600


def sentences(text):
    clean = " ".join(str(text or "").split())
    # Preserve decimals and common abbreviations when splitting prose.
    protected = re.sub(r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|e\.g|i\.e)\.",
                       lambda match: match.group(0).replace(".", "\u2024"), clean, flags=re.I)
    return [part.replace("\u2024", ".").strip() for part in
            re.split(r'(?<=[.!?])\s+(?=[\w\"\u201c\u2018])', protected) if part.strip()]


def paragraph_html(text):
    return "\n".join(f"<p>{html.escape(sentence)}</p>" for sentence in sentences(text))


class _ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.parts, self.tag, self.skip = [], [], "p", 0

    def flush(self):
        text = " ".join("".join(self.parts).split())
        if text:
            self.blocks.append((self.tag, text))
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "iframe", "object"):
            self.skip += 1
        if self.skip:
            return
        if tag in ("p", "h1", "h2", "h3", "li", "div", "section", "br"):
            self.flush()
            self.tag = tag if tag in ("h2", "h3") else "p"

    def handle_endtag(self, tag):
        if tag in ("script", "style", "iframe", "object") and self.skip:
            self.skip -= 1
            return
        if not self.skip and tag in ("p", "h1", "h2", "h3", "li", "div", "section"):
            self.flush()
            self.tag = "p"

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def normalize_article(source):
    """Only editorial headings and one-sentence paragraphs enter the CMS."""
    parser = _ArticleParser()
    parser.feed(str(source or ""))
    parser.flush()
    return "\n".join(f"<{tag}>{html.escape(text)}</{tag}>" if tag in ("h2", "h3")
                     else paragraph_html(text) for tag, text in parser.blocks)


def word_count(source):
    parser = _ArticleParser()
    parser.feed(str(source or ""))
    parser.flush()
    return len(re.findall(r"\b\w+(?:['’\-]\w+)*\b", " ".join(text for _, text in parser.blocks)))


def viewing_article(title, summary="", niche=""):
    title = english_or_default(title, "Original Video")
    context = english_or_default(summary)[:2400]
    niche = english_or_default(niche)
    blocks = [
        ("h2", title),
        ("p", f"The full recording behind {title} gives you more room to follow the sequence than a short highlight can offer."),
        ("p", "Watch for the details that connect one moment to the next, then use the full video player at the end of this article to see them in context."),
    ]
    if context:
        blocks += [("h3", "From the source description"), ("p", context)]
    if niche:
        blocks.append(("p", f"This viewing guide focuses on {niche}, using the title and available source description as its starting point."))
    blocks += [
        ("h3", "How to examine the original sequence"),
        ("p", "Begin with the opening of the complete recording and follow it at normal speed before returning to the selected moment. The first viewing gives you a sense of the camera position, the pace of the footage, and the material included around the highlight. Keep the title in mind as a guide to the subject, while allowing the recording itself to establish what is visible. A title can raise a question about a scene, but the surrounding footage is what lets you assess that question."),
        ("p", f"When you reach the passage associated with {title}, notice how it begins and what changes as it continues. You can pause to look at a detail and then replay the preceding seconds to understand its place in the sequence. Make a note of the timestamp if you want to return to it later. This is especially useful when the highlight is brief, because the relevant context may begin before the selected clip or continue after it ends."),
        ("p", "The reference images placed through this article give you visual points to return to while watching. A still can make a small detail easier to notice, while movement and timing require the recording. Compare each reference point with what comes before and after it in the player. If a camera change, replay, or edit appears, check how it affects the sequence you are following. Returning to the complete passage helps keep your interpretation connected to the available footage."),
        ("h3", "Look beyond the short highlight"),
        ("p", "On a second viewing, focus on the transition into the selected passage. The position of the camera and the people or objects in frame can help you understand what the recording shows at that point. Then continue past the highlight instead of stopping at the cut. Following the next part of the source may help explain how the scene develops. When the footage leaves a detail unclear, keep that question open and compare it with the wider sequence."),
        ("p", "Sound can also change how a moment is understood. Listen to any available dialogue or commentary alongside the visible action, and replay a passage if the words are difficult to hear. Check whether an on-screen caption describes the scene or adds an interpretation. You can compare those elements without assuming that every label or subtitle has been independently verified. The full recording gives you the opportunity to make that comparison at your own pace."),
        ("p", "If you want to share a detail with someone else, use its timestamp so they can see the same passage. Explain what you noticed before assigning a reason for it. Another viewer may focus on a different part of the frame or a different point in the sequence. Returning to the same source gives both of you a clear reference for discussing what appears on screen. It also makes it easier to distinguish a visible detail from a conclusion about it."),
        ("h3", "What the footage can and cannot confirm"),
        ("p", "A recording presents what its camera and microphone captured, with limits set by its viewpoint and duration. Events outside the frame, material recorded before it begins, and what happens after it ends may remain unknown. Keep those limits in mind when considering the subject named in the title. If you need a claim beyond the recording, look for a relevant independent source. The available description can help you locate the subject, while the footage remains the reference for the visible sequence."),
        ("p", "Before deciding what a highlight means, compare the opening, middle, and closing parts of the relevant passage. Look for a detail you can point to directly, and note whether it stays visible as the scene continues. A short extract may give you a reason to watch, while the longer version lets you review timing and context. Take a moment to revisit the source if your first impression depends on a single frame or an abrupt transition."),
        ("h3", "Watch the full video below"),
        ("p", f"Ready to follow the complete sequence behind {title}? Scroll to the full video player below and start from the beginning of the original recording. You can pause, replay, and compare the reference images as you go. Pay attention to the moments around the highlight and form your own view from the available footage. Return to the passage that caught your attention and see how it fits into the full recording."),
    ]
    return "\n".join(f"<{tag}>{html.escape(text)}</{tag}>" if tag in ("h2", "h3")
                     else paragraph_html(text) for tag, text in blocks)
