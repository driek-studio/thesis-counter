from __future__ import annotations

from core.models import Line

DUTCH_MARKERS = {"de", "het", "van", "een", "en", "is", "dat", "voor", "met", "zijn", "op", "aan", "niet", "ook", "wordt"}
ENGLISH_MARKERS = {"the", "of", "and", "a", "to", "in", "is", "that", "for", "with", "on", "not", "also", "are", "this"}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "total_included": {"en": "Included words", "nl": "Meegetelde woorden"},
    "total_excluded": {"en": "Excluded words", "nl": "Uitgesloten woorden"},
    "total_document": {"en": "Document total", "nl": "Document totaal"},
    "profile": {"en": "Profile", "nl": "Profiel"},
    "max_words": {"en": "Maximum words", "nl": "Maximum woorden"},
    "status": {"en": "Status", "nl": "Status"},
    "within_limit": {"en": "Within limit", "nl": "Binnen de grens"},
    "over_limit": {"en": "Over limit", "nl": "Boven de grens"},
    "no_limit": {"en": "No limit set", "nl": "Geen limiet ingesteld"},
    "section": {"en": "Section", "nl": "Sectie"},
    "level": {"en": "Level", "nl": "Niveau"},
    "words_included": {"en": "Words included", "nl": "Woorden inbegrepen"},
    "words_excluded": {"en": "Words excluded", "nl": "Woorden uitgesloten"},
    "exclusion_reasons": {"en": "Exclusion reasons", "nl": "Redenen uitsluiting"},
    "report_title": {"en": "Thesis Word Count Report", "nl": "Thesis woordentelling rapport"},
    "section_breakdown": {"en": "Section Breakdown", "nl": "Sectie-overzicht"},
    "file": {"en": "File", "nl": "Bestand"},
    "language": {"en": "Language", "nl": "Taal"},
    "language_nl": {"en": "Dutch", "nl": "Nederlands"},
    "language_en": {"en": "English", "nl": "Engels"},
    "no_text_layer": {"en": "This PDF has no selectable text. The tool cannot count words in scanned documents.", "nl": "Deze PDF heeft geen selecteerbare tekst. De tool kan geen woorden tellen in gescande documenten."},
    "encrypted_pdf": {"en": "This PDF is encrypted. Please provide the password or use an unencrypted version.", "nl": "Deze PDF is versleuteld. Geef het wachtwoord op of gebruik een onversleutelde versie."},
    "analysis_complete": {"en": "Analysis complete", "nl": "Analyse voltooid"},
    "choose_pdf": {"en": "Choose a PDF file", "nl": "Kies een PDF-bestand"},
    "choose_profile": {"en": "Choose a profile", "nl": "Kies een profiel"},
    "analyze": {"en": "Analyze", "nl": "Analyseer"},
    "export": {"en": "Export", "nl": "Exporteer"},
}


def detect_language(lines: list[Line]) -> str:
    nl_count = 0
    en_count = 0
    for line in lines:
        for token in line.tokens:
            word = token.text.lower()
            if word in DUTCH_MARKERS:
                nl_count += 1
            if word in ENGLISH_MARKERS:
                en_count += 1
    if nl_count > en_count * 1.5:
        return "nl"
    return "en"


def t(key: str, lang: str) -> str:
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("en", key))
