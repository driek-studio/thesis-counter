from __future__ import annotations

import csv
import io
import json
from datetime import date
from pathlib import Path

from core.i18n import t
from core.models import AnalysisResult


def result_to_dict(result: AnalysisResult) -> dict:
    return {
        "file": result.file_path,
        "profile": result.profile_id,
        "language": result.language,
        "total_included": result.total_included,
        "total_excluded": result.total_excluded,
        "total_document": result.total_included + result.total_excluded,
        "sections": [
            {
                "title": s.title,
                "level": s.level,
                "word_count": s.word_count,
                "excluded_word_count": s.excluded_word_count,
                "included": s.included,
                "exclusion_reasons": s.exclusion_reasons,
            }
            for s in result.sections
        ],
    }


def export_json(result: AnalysisResult, output_path: str | Path) -> None:
    data = result_to_dict(result)
    Path(output_path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_csv(result: AnalysisResult, output_path: str | Path) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "level", "word_count", "excluded_word_count", "included", "exclusion_reasons"])
        for s in result.sections:
            writer.writerow([
                s.title,
                s.level,
                s.word_count,
                s.excluded_word_count,
                s.included,
                "; ".join(s.exclusion_reasons),
            ])
        writer.writerow([])
        writer.writerow(["TOTAL", "", result.total_included, result.total_excluded, "", ""])


def export_text(result: AnalysisResult, output_path: str | Path, lang: str = "en") -> None:
    lines: list[str] = []
    lines.append(t("report_title", lang))
    lines.append("=" * len(lines[0]))
    lines.append(f"{t('file', lang)}: {result.file_path}")
    lines.append(f"{t('profile', lang)}: {result.profile_id}")
    lines.append(f"{t('language', lang)}: {t(f'language_{result.language}', lang)}")
    lines.append("")

    total = result.total_included + result.total_excluded
    lines.append(f"{t('total_included', lang)}: {result.total_included:,}")
    lines.append(f"{t('total_excluded', lang)}: {result.total_excluded:,}")
    lines.append(f"{t('total_document', lang)}: {total:,}")
    lines.append("")

    lines.append(t("section_breakdown", lang))
    lines.append("-" * len(lines[-1]))

    for s in result.sections:
        mark = "V" if s.included else "X"
        reason_str = f" -- {'; '.join(s.exclusion_reasons)}" if s.exclusion_reasons else ""
        count = s.word_count if s.included else s.excluded_word_count
        lines.append(f"[{mark}] {s.title} ({count:,} {t('words_included' if s.included else 'words_excluded', lang)}){reason_str}")

    lines.append("")
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def generate_output_path(pdf_path: str | Path, profile_id: str, ext: str) -> str:
    stem = Path(pdf_path).stem
    today = date.today().strftime("%Y%m%d")
    return f"{stem}_{profile_id}_{today}.{ext}"
