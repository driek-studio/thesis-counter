from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from core.i18n import detect_language
from core.models import AnalysisResult, Heading, Line, Profile, RuleSet, Section
from core.parser import parse_pdf

WORD_RE = re.compile(r"[\w]", re.UNICODE)
PURE_NUMBER_RE = re.compile(r"^\d+([.,]\d+)*$")

RULE_TO_LEXICON = {
    "exclude_front_matter": "front_matter",
    "exclude_toc": "toc",
    "exclude_abstract": "abstract",
    "exclude_preface": "preface",
    "exclude_appendices": "appendices",
    "exclude_references": "references",
}


def _profiles_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent.parent
    return base / "profiles"


def load_profile(profile_id: str) -> Profile:
    path = _profiles_dir() / f"{profile_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rules_data = data.get("rules", {})
    rules = RuleSet(**{k: v for k, v in rules_data.items() if hasattr(RuleSet, k)})
    return Profile(
        id=data["id"],
        name=data.get("name", data["id"]),
        max_words=data.get("max_words", 0),
        rules=rules,
        lexicon=data.get("lexicon", {}),
    )


def list_profiles() -> list[str]:
    profiles_dir = _profiles_dir()
    if not profiles_dir.exists():
        return []
    return sorted(p.stem for p in profiles_dir.glob("*.json"))


def build_sections(lines: list[Line], headings: list[Heading]) -> list[Section]:
    lines_sorted = sorted(lines, key=lambda ln: (ln.page, ln.top))
    headings_sorted = sorted(headings, key=lambda h: (h.page, h.top))

    def pos_before(page_a: int, top_a: float, page_b: int, top_b: float) -> bool:
        return (page_a < page_b) or (page_a == page_b and top_a < top_b)

    sections: list[Section] = []

    # Lines before the first heading become "Preamble"
    if headings_sorted:
        first_h = headings_sorted[0]
        preamble_lines = [
            ln for ln in lines_sorted
            if pos_before(ln.page, ln.top, first_h.page, first_h.top)
        ]
        if preamble_lines:
            sections.append(Section(
                title="Preamble",
                level=0,
                start_page=preamble_lines[0].page,
                start_top=preamble_lines[0].top,
                end_page=first_h.page,
                end_top=first_h.top,
                lines=preamble_lines,
            ))

    for i, h in enumerate(headings_sorted):
        next_h = headings_sorted[i + 1] if i + 1 < len(headings_sorted) else None
        content: list[Line] = []
        for ln in lines_sorted:
            # Must be at or after heading position
            if pos_before(ln.page, ln.top, h.page, h.top):
                continue
            # Skip the heading line itself
            if ln.page == h.page and abs(ln.top - h.top) < 0.5:
                continue
            # Must be before next heading
            if next_h and not pos_before(ln.page, ln.top, next_h.page, next_h.top):
                continue
            content.append(ln)

        last_line = lines_sorted[-1] if lines_sorted else None
        sections.append(Section(
            title=h.text,
            level=h.level,
            start_page=h.page,
            start_top=h.top,
            end_page=next_h.page if next_h else (last_line.page if last_line else h.page),
            end_top=next_h.top if next_h else (last_line.bottom if last_line else h.top),
            lines=content,
        ))

    if not headings_sorted and lines_sorted:
        sections.append(Section(
            title="Document",
            level=1,
            start_page=lines_sorted[0].page,
            start_top=lines_sorted[0].top,
            end_page=lines_sorted[-1].page,
            end_top=lines_sorted[-1].bottom,
            lines=lines_sorted,
        ))

    return sections


def label_sections(sections: list[Section], profile: Profile) -> None:
    rules = profile.rules
    for section in sections:
        title_lower = section.title.strip().lower()

        if section.title == "Preamble":
            if rules.exclude_front_matter:
                section.included = False
                section.exclusion_reasons.append("exclude_front_matter")
            continue

        for rule_name, lexicon_key in RULE_TO_LEXICON.items():
            rule_enabled = getattr(rules, rule_name, False)
            if not rule_enabled:
                continue
            keywords = profile.lexicon.get(lexicon_key, [])
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    section.included = False
                    section.exclusion_reasons.append(rule_name)
                    break


def count_section_words(section: Section, rules: RuleSet) -> None:
    included = 0
    excluded = 0

    for line in section.lines:
        for token in line.tokens:
            text = token.text
            if not WORD_RE.search(text):
                continue
            if not rules.numbers_as_words and PURE_NUMBER_RE.match(text):
                continue
            if section.included:
                included += 1
            else:
                excluded += 1

    section.word_count = included
    section.excluded_word_count = excluded


def analyze(
    pdf_path: str | Path,
    profile: Profile | None = None,
    profile_id: str = "cmd_zuyd",
    lang_override: str | None = None,
) -> AnalysisResult:
    if profile is None:
        profile = load_profile(profile_id)

    lines, headings, page_count = parse_pdf(pdf_path)

    if not lines:
        return AnalysisResult(
            file_path=str(pdf_path),
            profile_id=profile.id,
            language=lang_override or "en",
            total_included=0,
            total_excluded=0,
            sections=[],
        )

    language = lang_override or detect_language(lines)
    sections = build_sections(lines, headings)
    label_sections(sections, profile)

    for section in sections:
        count_section_words(section, profile.rules)

    return AnalysisResult(
        file_path=str(pdf_path),
        profile_id=profile.id,
        language=language,
        total_included=sum(s.word_count for s in sections),
        total_excluded=sum(s.excluded_word_count for s in sections),
        sections=sections,
    )
