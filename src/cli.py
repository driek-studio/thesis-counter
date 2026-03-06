from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from core.engine import analyze, list_profiles, load_profile
from core.export import export_csv, export_json, export_text, generate_output_path

app = typer.Typer(help="Thesis word counter — count words in thesis PDFs with configurable rules.")


@app.command()
def count(
    pdf: Path = typer.Argument(..., help="Path to the thesis PDF file", exists=True),
    profile: str = typer.Option("cmd_zuyd", "--profile", "-p", help="Profile ID to use"),
    output_format: str = typer.Option("text", "--format", "-f", help="Output format: text, json, csv"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path (default: auto-generated)"),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Language override: en, nl (default: auto-detect)"),
    max_words: Optional[int] = typer.Option(None, "--max-words", "-m", help="Override word limit (0 = no limit)"),
    enable: list[str] = typer.Option([], "--enable", help="Enable a rule, e.g. numbers_as_words"),
    disable: list[str] = typer.Option([], "--disable", help="Disable a rule, e.g. exclude_references"),
) -> None:
    """Analyze a thesis PDF and count words per section."""
    prof = load_profile(profile)
    if max_words is not None:
        prof.max_words = max_words
    for rule in enable:
        if hasattr(prof.rules, rule):
            setattr(prof.rules, rule, True)
        else:
            typer.echo(f"Warning: unknown rule '{rule}'", err=True)
    for rule in disable:
        if hasattr(prof.rules, rule):
            setattr(prof.rules, rule, False)
        else:
            typer.echo(f"Warning: unknown rule '{rule}'", err=True)
    result = analyze(pdf, profile=prof, lang_override=lang)

    if output is None:
        ext = {"json": "json", "csv": "csv", "text": "txt"}.get(output_format, "txt")
        output = Path(generate_output_path(str(pdf), profile, ext))

    report_lang = result.language

    if output_format == "json":
        export_json(result, output)
    elif output_format == "csv":
        export_csv(result, output)
    else:
        export_text(result, output, lang=report_lang)

    typer.echo(f"Included: {result.total_included:,} words")
    typer.echo(f"Excluded: {result.total_excluded:,} words")
    typer.echo(f"Total:    {result.total_included + result.total_excluded:,} words")
    if prof.max_words > 0:
        status = "WITHIN LIMIT" if result.total_included <= prof.max_words else "OVER LIMIT"
        typer.echo(f"Limit:    {prof.max_words:,} ({status})")
    typer.echo(f"Report:   {output}")


@app.command()
def profiles() -> None:
    """List available counting profiles."""
    for pid in list_profiles():
        prof = load_profile(pid)
        limit = f"max {prof.max_words:,}" if prof.max_words > 0 else "no limit"
        typer.echo(f"  {prof.id:<20} {prof.name:<20} ({limit})")
