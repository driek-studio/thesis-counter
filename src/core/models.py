from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Token:
    text: str
    page: int
    x0: float
    top: float
    x1: float
    bottom: float
    fontname: str
    size: float


@dataclass
class Line:
    page: int
    top: float
    bottom: float
    text: str
    avg_size: float
    fontnames: set[str]
    tokens: list[Token]


@dataclass
class Heading:
    page: int
    top: float
    text: str
    level: int
    score: float


@dataclass
class Section:
    title: str
    level: int
    start_page: int
    start_top: float
    end_page: int
    end_top: float
    lines: list[Line]
    word_count: int = 0
    excluded_word_count: int = 0
    exclusion_reasons: list[str] = field(default_factory=list)
    included: bool = True


@dataclass
class RuleSet:
    exclude_front_matter: bool = True
    exclude_toc: bool = True
    exclude_abstract: bool = True
    exclude_preface: bool = True
    exclude_appendices: bool = True
    exclude_references: bool = True
    exclude_headers_footers: bool = True
    exclude_captions: bool = True
    merge_hyphenation: bool = True
    numbers_as_words: bool = False


@dataclass
class Profile:
    id: str
    name: str
    max_words: int
    rules: RuleSet
    lexicon: dict[str, list[str]]


@dataclass
class AnalysisResult:
    file_path: str
    profile_id: str
    language: str
    total_included: int
    total_excluded: int
    sections: list[Section]
