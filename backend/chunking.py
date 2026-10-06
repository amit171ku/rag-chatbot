import re
from collections import Counter

CHUNK_SIZE = 700       # characters (smaller = sharper retrieval for slide decks)
CHUNK_OVERLAP = 120


def strip_repeated_lines(text: str, min_repeats: int = 4) -> str:
    """Drop short lines that repeat many times (slide footers, page headers)."""
    lines = text.splitlines()
    counts = Counter(l.strip() for l in lines if l.strip())
    boiler = {l for l, c in counts.items() if c >= min_repeats and len(l) < 200}
    return "\n".join(l for l in lines if l.strip() not in boiler)


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")

    text = strip_repeated_lines(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))

        if end < len(text):
            # Prefer breaking at a paragraph, then sentence, then space
            window = text[start:end]
            for sep in ("\n\n", ". ", "\n", " "):
                cut = window.rfind(sep)
                if cut > size * 0.5:
                    end = start + cut + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break
        start = max(end - overlap, start + 1)  # always advance

    return chunks