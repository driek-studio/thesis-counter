from core.models import Line, Token
from core.parser import (
    cluster_into_lines,
    detect_headings,
    detect_repeated_headers_footers,
    estimate_body_font_size,
    heading_level,
    heading_score,
)


def _tok(text: str, page: int = 0, x0: float = 0, top: float = 0, size: float = 12.0, fontname: str = "Regular") -> Token:
    return Token(text=text, page=page, x0=x0, top=top, x1=x0 + len(text) * 6, bottom=top + size, fontname=fontname, size=size)


def _line(text: str, page: int = 0, top: float = 100, avg_size: float = 12.0, fontnames: set[str] | None = None) -> Line:
    tokens = [_tok(w, page=page, top=top, size=avg_size) for w in text.split()]
    return Line(page=page, top=top, bottom=top + avg_size, text=text, avg_size=avg_size, fontnames=fontnames or {"Regular"}, tokens=tokens)


class TestClusterIntoLines:
    def test_same_line_grouped(self):
        tokens = [
            _tok("Hello", page=0, x0=10, top=100),
            _tok("world", page=0, x0=50, top=101),  # within y_tol
        ]
        lines = cluster_into_lines(tokens)
        assert len(lines) == 1
        assert lines[0].text == "Hello world"

    def test_different_lines_split(self):
        tokens = [
            _tok("Line one", page=0, x0=10, top=100),
            _tok("Line two", page=0, x0=10, top=120),
        ]
        lines = cluster_into_lines(tokens)
        assert len(lines) == 2

    def test_different_pages_split(self):
        tokens = [
            _tok("Page one", page=0, x0=10, top=100),
            _tok("Page two", page=1, x0=10, top=100),
        ]
        lines = cluster_into_lines(tokens)
        assert len(lines) == 2

    def test_empty_tokens(self):
        assert cluster_into_lines([]) == []

    def test_x_ordering_within_line(self):
        tokens = [
            _tok("world", page=0, x0=50, top=100),
            _tok("Hello", page=0, x0=10, top=100),
        ]
        lines = cluster_into_lines(tokens)
        assert lines[0].text == "Hello world"


class TestDetectRepeatedHeadersFooters:
    def test_repeated_header_detected(self):
        lines = [_line("Page Header", page=i, top=10) for i in range(10)]
        lines += [_line("Body text here", page=i, top=200) for i in range(10)]
        result = detect_repeated_headers_footers(lines, page_count=10)
        assert "Page Header" in result

    def test_non_repeated_not_flagged(self):
        lines = [_line("Unique title", page=0, top=10)]
        lines += [_line("Body text", page=i, top=200) for i in range(10)]
        result = detect_repeated_headers_footers(lines, page_count=10)
        assert "Unique title" not in result

    def test_body_text_not_flagged(self):
        lines = [_line("Repeated body", page=i, top=200) for i in range(10)]
        result = detect_repeated_headers_footers(lines, page_count=10)
        assert len(result) == 0


class TestEstimateBodyFontSize:
    def test_median_calculation(self):
        lines = [_line("text", avg_size=12.0) for _ in range(20)]
        lines.append(_line("heading", avg_size=18.0))  # top 5% outlier
        size = estimate_body_font_size(lines)
        assert size == 12.0

    def test_empty_lines(self):
        assert estimate_body_font_size([]) == 0.0


class TestHeadingScore:
    def test_large_font_scores_high(self):
        ln = _line("Introduction", avg_size=16.0)
        score = heading_score(ln, body_size=12.0)
        assert score >= 2.0

    def test_bold_adds_score(self):
        ln = _line("Title", fontnames={"TimesNewRoman-Bold"})
        score = heading_score(ln, body_size=12.0)
        assert score >= 1.0

    def test_numbered_heading(self):
        ln = _line("1.2 Methods")
        score = heading_score(ln, body_size=12.0)
        assert score >= 1.5

    def test_keyword_heading(self):
        ln = _line("Conclusie")
        score = heading_score(ln, body_size=12.0)
        assert score >= 1.0

    def test_caption_penalized(self):
        ln = _line("Figuur 1: Example caption")
        score = heading_score(ln, body_size=12.0)
        assert score <= 0.0

    def test_single_digit_penalized(self):
        ln = _line("3")
        score = heading_score(ln, body_size=12.0)
        assert score < 0.0

    def test_body_text_low_score(self):
        ln = _line("This is a normal sentence about something.")
        score = heading_score(ln, body_size=12.0)
        assert score < HEADING_THRESHOLD


class TestHeadingLevel:
    def test_single_number(self):
        assert heading_level("1 Introduction", 16.0, 12.0) == 1

    def test_dotted_number(self):
        assert heading_level("1.2 Methods", 14.0, 12.0) == 2

    def test_triple_dotted(self):
        assert heading_level("1.2.3 Sub method", 13.0, 12.0) == 3

    def test_no_number_large_font(self):
        assert heading_level("Introduction", 20.0, 12.0) == 1

    def test_no_number_medium_font(self):
        assert heading_level("Methods", 16.0, 12.0) == 2


class TestDetectHeadings:
    def test_heading_detected(self):
        body_lines = [_line(f"Body text {i}", top=100 + i * 20) for i in range(20)]
        heading_line = _line("1 Introduction", avg_size=16.0, fontnames={"Bold"}, top=80)
        all_lines = [heading_line] + body_lines
        headings = detect_headings(all_lines, set())
        assert len(headings) >= 1
        assert any("Introduction" in h.text for h in headings)

    def test_repeated_hf_excluded(self):
        body_lines = [_line(f"Body {i}", top=100 + i * 20) for i in range(20)]
        hf_line = _line("Page Header", avg_size=16.0, fontnames={"Bold"}, top=10)
        all_lines = [hf_line] + body_lines
        headings = detect_headings(all_lines, {"Page Header"})
        assert not any("Page Header" in h.text for h in headings)


HEADING_THRESHOLD = 2.5
