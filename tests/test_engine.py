from core.models import Heading, Line, Profile, RuleSet, Section, Token
from core.engine import build_sections, count_section_words, label_sections, load_profile, list_profiles


def _tok(text: str, page: int = 0, top: float = 100, size: float = 12.0) -> Token:
    return Token(text=text, page=page, x0=0, top=top, x1=len(text) * 6, bottom=top + size, fontname="Regular", size=size)


def _line(text: str, page: int = 0, top: float = 100, avg_size: float = 12.0) -> Line:
    tokens = [_tok(w, page=page, top=top, size=avg_size) for w in text.split()]
    return Line(page=page, top=top, bottom=top + avg_size, text=text, avg_size=avg_size, fontnames={"Regular"}, tokens=tokens)


def _heading(text: str, page: int = 0, top: float = 50, level: int = 1) -> Heading:
    return Heading(page=page, top=top, text=text, level=level, score=3.0)


def _profile(**overrides) -> Profile:
    rules = RuleSet(**(overrides.pop("rules", {})))
    defaults = {
        "id": "test",
        "name": "Test",
        "max_words": 0,
        "rules": rules,
        "lexicon": {
            "front_matter": ["titelblad"],
            "toc": ["inhoudsopgave"],
            "abstract": ["samenvatting", "abstract"],
            "preface": ["voorwoord"],
            "appendices": ["bijlage", "bijlagen", "appendix"],
            "references": ["referenties", "references", "literatuurlijst"],
        },
    }
    defaults.update(overrides)
    return Profile(**defaults)


class TestBuildSections:
    def test_single_heading(self):
        lines = [
            _line("Some preamble text", page=0, top=30),
            _line("Body paragraph one", page=0, top=80),
            _line("Body paragraph two", page=0, top=100),
        ]
        headings = [_heading("Introduction", page=0, top=60)]
        sections = build_sections(lines, headings)
        assert len(sections) == 2  # Preamble + Introduction
        assert sections[0].title == "Preamble"
        assert sections[1].title == "Introduction"

    def test_multiple_headings(self):
        lines = [
            _line("Intro text", page=0, top=80),
            _line("Method text", page=0, top=180),
        ]
        headings = [
            _heading("Introduction", page=0, top=60),
            _heading("Methods", page=0, top=160),
        ]
        sections = build_sections(lines, headings)
        titled = [s for s in sections if s.title != "Preamble"]
        assert len(titled) == 2
        assert titled[0].title == "Introduction"
        assert titled[1].title == "Methods"

    def test_no_headings(self):
        lines = [_line("Some text", page=0, top=100)]
        sections = build_sections(lines, [])
        assert len(sections) == 1
        assert sections[0].title == "Document"

    def test_empty(self):
        sections = build_sections([], [])
        assert sections == []


class TestLabelSections:
    def test_front_matter_excluded(self):
        profile = _profile()
        sections = [
            Section(title="Voorwoord", level=1, start_page=0, start_top=0, end_page=0, end_top=100, lines=[]),
            Section(title="Introduction", level=1, start_page=0, start_top=100, end_page=0, end_top=200, lines=[]),
        ]
        label_sections(sections, profile)
        assert not sections[0].included
        assert "exclude_preface" in sections[0].exclusion_reasons
        assert sections[1].included

    def test_references_excluded(self):
        profile = _profile()
        sections = [
            Section(title="Literatuurlijst", level=1, start_page=0, start_top=0, end_page=0, end_top=100, lines=[]),
        ]
        label_sections(sections, profile)
        assert not sections[0].included
        assert "exclude_references" in sections[0].exclusion_reasons

    def test_appendix_excluded(self):
        profile = _profile()
        sections = [
            Section(title="Bijlagen", level=1, start_page=0, start_top=0, end_page=0, end_top=100, lines=[]),
        ]
        label_sections(sections, profile)
        assert not sections[0].included

    def test_rule_disabled_not_excluded(self):
        profile = _profile(rules={"exclude_references": False})
        sections = [
            Section(title="Literatuurlijst", level=1, start_page=0, start_top=0, end_page=0, end_top=100, lines=[]),
        ]
        label_sections(sections, profile)
        assert sections[0].included

    def test_preamble_excluded(self):
        profile = _profile()
        sections = [
            Section(title="Preamble", level=0, start_page=0, start_top=0, end_page=0, end_top=50, lines=[]),
        ]
        label_sections(sections, profile)
        assert not sections[0].included


class TestCountSectionWords:
    def test_basic_count(self):
        section = Section(
            title="Test", level=1, start_page=0, start_top=0, end_page=0, end_top=100,
            lines=[_line("Hello world foo bar")],
        )
        count_section_words(section, RuleSet())
        assert section.word_count == 4

    def test_excluded_section(self):
        section = Section(
            title="Test", level=1, start_page=0, start_top=0, end_page=0, end_top=100,
            lines=[_line("Hello world")],
            included=False,
        )
        count_section_words(section, RuleSet())
        assert section.word_count == 0
        assert section.excluded_word_count == 2

    def test_numbers_excluded_by_default(self):
        section = Section(
            title="Test", level=1, start_page=0, start_top=0, end_page=0, end_top=100,
            lines=[_line("There are 42 items")],
        )
        count_section_words(section, RuleSet(numbers_as_words=False))
        assert section.word_count == 3  # "There", "are", "items" — not "42"

    def test_numbers_included_when_enabled(self):
        section = Section(
            title="Test", level=1, start_page=0, start_top=0, end_page=0, end_top=100,
            lines=[_line("There are 42 items")],
        )
        count_section_words(section, RuleSet(numbers_as_words=True))
        assert section.word_count == 4


class TestProfileLoading:
    def test_load_cmd_zuyd(self):
        profile = load_profile("cmd_zuyd")
        assert profile.id == "cmd_zuyd"
        assert profile.max_words == 15000
        assert profile.rules.exclude_front_matter is True

    def test_load_apa_university(self):
        profile = load_profile("apa_university")
        assert profile.id == "apa_university"
        assert profile.max_words == 0

    def test_list_profiles(self):
        profiles = list_profiles()
        assert "cmd_zuyd" in profiles
        assert "apa_university" in profiles
