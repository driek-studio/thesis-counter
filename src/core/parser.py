from __future__ import annotations

import re
import statistics
from pathlib import Path

import pdfplumber

from core.models import Heading, Line, Token

HEADING_NUMBER_RE = re.compile(r"^\s*(\d{1,2})(\.\d{1,2})*\.?\s+.+$")
CHAPTER_RE = re.compile(r"^\s*(hoofdstuk|chapter)\s+\d+", re.IGNORECASE)
CAPTION_RE = re.compile(
    r"^\s*(figuur|figure|fig\.|tabel|table|afbeelding)\s+\d+(\.\d+)?\s*[:.]\s+",
    re.IGNORECASE,
)
SECTION_KEYWORD_RE = re.compile(
    r"^\s*(inhoudsopgave|voorwoord|samenvatting|abstract|introduction|inleiding"
    r"|conclusie|conclusion|discussie|discussion|methode|methodology|method"
    r"|resultaten|results|references|bibliography|literatuurlijst|literatuur"
    r"|referenties|bijlage|bijlagen|appendix|appendices|dankwoord"
    r"|acknowledgements|preface|foreword)\s*$",
    re.IGNORECASE,
)

Y_TOLERANCE = 2.5
HEADER_FOOTER_ZONE = 60.0
HEADER_FOOTER_RATIO = 0.6
HEADING_THRESHOLD = 2.5


def extract_tokens(path: str | Path) -> tuple[list[Token], int]:
    tokens: list[Token] = []
    page_count = 0
    with pdfplumber.open(str(path)) as pdf:
        page_count = len(pdf.pages)
        for page_index, page in enumerate(pdf.pages):
            words = page.extract_words(
                extra_attrs=["fontname", "size"],
                keep_blank_chars=False,
                use_text_flow=False,
            )
            for w in words:
                text = (w.get("text") or "").strip()
                if not text:
                    continue
                tokens.append(Token(
                    text=text,
                    page=page_index,
                    x0=float(w["x0"]),
                    top=float(w["top"]),
                    x1=float(w["x1"]),
                    bottom=float(w["bottom"]),
                    fontname=str(w.get("fontname") or ""),
                    size=float(w.get("size") or 0.0),
                ))
    return tokens, page_count


def cluster_into_lines(tokens: list[Token], y_tol: float = Y_TOLERANCE) -> list[Line]:
    sorted_tokens = sorted(tokens, key=lambda t: (t.page, t.top, t.x0))
    lines: list[Line] = []
    current: list[Token] = []

    def flush() -> None:
        if not current:
            return
        by_x = sorted(current, key=lambda t: t.x0)
        text = " ".join(t.text for t in by_x)
        sizes = [t.size for t in current if t.size > 0]
        avg_size = statistics.mean(sizes) if sizes else 0.0
        fontnames = {t.fontname for t in current}
        lines.append(Line(
            page=current[0].page,
            top=min(t.top for t in current),
            bottom=max(t.bottom for t in current),
            text=text.strip(),
            avg_size=avg_size,
            fontnames=fontnames,
            tokens=list(by_x),
        ))

    for tok in sorted_tokens:
        if not current:
            current = [tok]
            continue
        same_page = tok.page == current[0].page
        close_y = abs(tok.top - current[0].top) <= y_tol
        if same_page and close_y:
            current.append(tok)
        else:
            flush()
            current = [tok]
    flush()
    return lines


def detect_repeated_headers_footers(
    lines: list[Line], page_count: int, page_heights: dict[int, float] | None = None
) -> set[str]:
    text_pages: dict[str, set[int]] = {}
    for ln in lines:
        in_top_zone = ln.top <= HEADER_FOOTER_ZONE
        in_bottom_zone = False
        if page_heights and ln.page in page_heights:
            in_bottom_zone = ln.bottom >= page_heights[ln.page] - HEADER_FOOTER_ZONE
        if not (in_top_zone or in_bottom_zone):
            continue
        key = ln.text.strip()
        if not key:
            continue
        if key not in text_pages:
            text_pages[key] = set()
        text_pages[key].add(ln.page)

    threshold = max(3, int(page_count * HEADER_FOOTER_RATIO))
    return {text for text, pages in text_pages.items() if len(pages) >= threshold}


def estimate_body_font_size(lines: list[Line]) -> float:
    sizes = [ln.avg_size for ln in lines if ln.avg_size > 0]
    if not sizes:
        return 0.0
    sizes.sort()
    cutoff = int(len(sizes) * 0.95)
    core = sizes[:max(cutoff, 1)]
    return statistics.median(core)


def heading_score(line: Line, body_size: float) -> float:
    if not line.text:
        return 0.0
    score = 0.0
    if body_size > 0:
        ratio = line.avg_size / body_size
        if ratio >= 1.25:
            score += 2.0
        elif ratio >= 1.10:
            score += 1.0

    if any("Bold" in fn or "bold" in fn or "Black" in fn or "SemiBold" in fn for fn in line.fontnames):
        score += 1.0

    if HEADING_NUMBER_RE.match(line.text) or CHAPTER_RE.match(line.text):
        score += 1.5

    if SECTION_KEYWORD_RE.match(line.text):
        score += 1.0

    if CAPTION_RE.match(line.text):
        score -= 1.0

    if len(line.text) <= 3 and line.text.isdigit():
        score -= 1.0

    return score


def heading_level(text: str, avg_size: float, body_size: float) -> int:
    m = re.match(r"^\s*(\d{1,2}(?:\.\d{1,2})*)", text)
    if m:
        dots = m.group(1).count(".")
        return 1 + dots

    if body_size > 0:
        ratio = avg_size / body_size
        if ratio >= 1.5:
            return 1
        if ratio >= 1.25:
            return 2
        return 3
    return 1


def detect_headings(lines: list[Line], repeated_hf: set[str]) -> list[Heading]:
    content_lines = [ln for ln in lines if ln.text.strip() not in repeated_hf]
    body_size = estimate_body_font_size(content_lines)

    headings: list[Heading] = []
    for ln in content_lines:
        score = heading_score(ln, body_size)
        if score >= HEADING_THRESHOLD:
            level = heading_level(ln.text, ln.avg_size, body_size)
            headings.append(Heading(
                page=ln.page,
                top=ln.top,
                text=ln.text.strip(),
                level=level,
                score=score,
            ))

    headings.sort(key=lambda h: (h.page, h.top))
    return headings


def parse_pdf(path: str | Path) -> tuple[list[Line], list[Heading], int]:
    tokens, page_count = extract_tokens(path)
    if not tokens:
        return [], [], page_count

    lines = cluster_into_lines(tokens)
    repeated_hf = detect_repeated_headers_footers(lines, page_count)
    filtered_lines = [ln for ln in lines if ln.text.strip() not in repeated_hf]
    headings = detect_headings(lines, repeated_hf)

    return filtered_lines, headings, page_count
