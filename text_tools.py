"""
Text utilities. Summarize/rewrite use a local frequency-based extractive
algorithm by default (no external dependency, always works). If an
ANTHROPIC_API_KEY env var is set, quality is upgraded to use Claude for
real abstractive summarization/rewriting — this is optional and the bot
works fully without it.
"""
import os
import re
from collections import Counter

_STOPWORDS = set(
    "a an the this that these those is are was were be been being have has had "
    "do does did will would shall should may might must can could of in on at to "
    "for with as by from up down out about into over after before between and or "
    "but if then so than too very just not no nor it its it's i you he she we they "
    "them his her their our your my me him us".split()
)


def word_count(text: str) -> dict:
    words = re.findall(r"\b\w+\b", text)
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if s.strip()]
    return {
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "")),
        "words": len(words),
        "sentences": len(sentences),
        "paragraphs": len([p for p in text.split("\n\n") if p.strip()]) or 1,
    }


def clean_text(text: str) -> str:
    text = text.replace("\u200b", "")  # zero-width space
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +\n", "\n", text)
    return text.strip()


def _extractive_summary(text: str, num_sentences: int = 3) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sentences) <= num_sentences:
        return text.strip()

    words = re.findall(r"\b\w+\b", text.lower())
    freqs = Counter(w for w in words if w not in _STOPWORDS)
    max_freq = max(freqs.values()) if freqs else 1

    scores = []
    for i, sent in enumerate(sentences):
        sent_words = re.findall(r"\b\w+\b", sent.lower())
        score = sum(freqs.get(w, 0) for w in sent_words) / max_freq
        score = score / (len(sent_words) + 1) * 10  # normalize against length
        scores.append((score, i, sent))

    top = sorted(scores, key=lambda x: x[0], reverse=True)[:num_sentences]
    top_sorted_by_position = sorted(top, key=lambda x: x[1])
    return " ".join(s for _, _, s in top_sorted_by_position)


def _try_anthropic(system: str, user_text: str) -> str | None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": user_text}],
        )
        return "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
    except Exception:
        return None


def summarize(text: str, num_sentences: int = 3) -> str:
    ai_result = _try_anthropic(
        "Summarize the user's text concisely and clearly. Reply with only the summary, no preamble.",
        text,
    )
    if ai_result:
        return ai_result
    return _extractive_summary(text, num_sentences)


def rewrite(text: str, style: str = "clearer") -> str:
    ai_result = _try_anthropic(
        f"Rewrite the user's text to be {style}, preserving the original meaning. "
        "Reply with only the rewritten text, no preamble.",
        text,
    )
    if ai_result:
        return ai_result
    # Local fallback: light cleanup only — no AI key configured
    cleaned = clean_text(text)
    return (
        "⚠️ No AI key configured, so here's a cleaned-up version instead of a true rewrite "
        "(set ANTHROPIC_API_KEY for real AI rewriting):\n\n" + cleaned
    )
