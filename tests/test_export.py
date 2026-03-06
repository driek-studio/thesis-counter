import json
import csv
from pathlib import Path

from core.models import AnalysisResult, Section
from core.export import export_csv, export_json, export_text, generate_output_path, result_to_dict


def _result() -> AnalysisResult:
    return AnalysisResult(
        file_path="thesis.pdf",
        profile_id="cmd_zuyd",
        language="nl",
        total_included=9390,
        total_excluded=4920,
        sections=[
            Section(title="Voorwoord", level=1, start_page=0, start_top=0, end_page=0, end_top=100, lines=[], word_count=0, excluded_word_count=420, included=False, exclusion_reasons=["exclude_preface"]),
            Section(title="Inleiding", level=1, start_page=1, start_top=0, end_page=2, end_top=100, lines=[], word_count=1240, excluded_word_count=0, included=True),
            Section(title="Conclusie", level=1, start_page=5, start_top=0, end_page=5, end_top=200, lines=[], word_count=650, excluded_word_count=0, included=True),
            Section(title="Literatuurlijst", level=1, start_page=6, start_top=0, end_page=7, end_top=100, lines=[], word_count=0, excluded_word_count=1800, included=False, exclusion_reasons=["exclude_references"]),
        ],
    )


class TestResultToDict:
    def test_structure(self):
        d = result_to_dict(_result())
        assert d["file"] == "thesis.pdf"
        assert d["profile"] == "cmd_zuyd"
        assert d["total_included"] == 9390
        assert d["total_excluded"] == 4920
        assert d["total_document"] == 14310
        assert len(d["sections"]) == 4


class TestExportJson:
    def test_valid_json(self, tmp_path: Path):
        out = tmp_path / "result.json"
        export_json(_result(), out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["total_included"] == 9390
        assert len(data["sections"]) == 4

    def test_unicode_safe(self, tmp_path: Path):
        out = tmp_path / "result.json"
        export_json(_result(), out)
        text = out.read_text(encoding="utf-8")
        assert "Literatuurlijst" in text


class TestExportCsv:
    def test_csv_rows(self, tmp_path: Path):
        out = tmp_path / "result.csv"
        export_csv(_result(), out)
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        header = rows[0]
        assert "title" in header
        assert "word_count" in header
        # 4 sections + header + empty row + total
        assert len(rows) == 7


class TestExportText:
    def test_text_report_nl(self, tmp_path: Path):
        out = tmp_path / "result.txt"
        export_text(_result(), out, lang="nl")
        text = out.read_text(encoding="utf-8")
        assert "Thesis woordentelling rapport" in text
        assert "Meegetelde woorden" in text
        assert "Voorwoord" in text

    def test_text_report_en(self, tmp_path: Path):
        out = tmp_path / "result.txt"
        export_text(_result(), out, lang="en")
        text = out.read_text(encoding="utf-8")
        assert "Thesis Word Count Report" in text
        assert "Included words" in text


class TestGenerateOutputPath:
    def test_format(self):
        path = generate_output_path("my_thesis.pdf", "cmd_zuyd", "json")
        assert path.startswith("my_thesis_cmd_zuyd_")
        assert path.endswith(".json")
