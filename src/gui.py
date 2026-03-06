from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from core.engine import analyze, list_profiles, load_profile
from core.export import export_csv, export_json, export_text, generate_output_path
from core.i18n import t
from core.models import AnalysisResult, Profile, RuleSet

try:
    import tkinterdnd2 as tkdnd
    HAS_DND = True
except ImportError:
    HAS_DND = False


RULE_LABELS = {
    "exclude_front_matter": {"en": "Exclude front matter", "nl": "Voorwerk uitsluiten"},
    "exclude_toc": {"en": "Exclude table of contents", "nl": "Inhoudsopgave uitsluiten"},
    "exclude_abstract": {"en": "Exclude abstract", "nl": "Samenvatting uitsluiten"},
    "exclude_preface": {"en": "Exclude preface", "nl": "Voorwoord uitsluiten"},
    "exclude_appendices": {"en": "Exclude appendices", "nl": "Bijlagen uitsluiten"},
    "exclude_references": {"en": "Exclude references", "nl": "Referenties uitsluiten"},
    "exclude_headers_footers": {"en": "Exclude headers/footers", "nl": "Kop-/voettekst uitsluiten"},
    "exclude_captions": {"en": "Exclude captions", "nl": "Bijschriften uitsluiten"},
    "merge_hyphenation": {"en": "Merge hyphenation", "nl": "Afbreekstreepjes samenvoegen"},
    "numbers_as_words": {"en": "Count numbers as words", "nl": "Nummers als woorden tellen"},
}


class ThesisCounterApp:
    def __init__(self) -> None:
        if HAS_DND:
            self.root = tkdnd.Tk()
        else:
            self.root = tk.Tk()
        self.root.title("Thesis Word Counter")
        self.root.geometry("700x550")
        self.root.minsize(600, 450)

        self.pdf_path: str | None = None
        self.result: AnalysisResult | None = None
        self.analyzed_profile: Profile | None = None
        self.lang = "en"
        self.rule_vars: dict[str, tk.BooleanVar] = {}
        self.max_words_var = tk.StringVar()

        self.container = ttk.Frame(self.root)
        self.container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.frames: dict[str, ttk.Frame] = {}
        self._build_file_screen()
        self._build_profile_screen()
        self._build_results_screen()

        self._show_frame("file")

    def _show_frame(self, name: str) -> None:
        for frame in self.frames.values():
            frame.pack_forget()
        self.frames[name].pack(fill=tk.BOTH, expand=True)

    # -- Screen 1: File selection --

    def _build_file_screen(self) -> None:
        frame = ttk.Frame(self.container)
        self.frames["file"] = frame

        ttk.Label(frame, text="Thesis Word Counter", font=("", 18, "bold")).pack(pady=(20, 10))

        drop_frame = ttk.LabelFrame(frame, text="PDF", padding=30)
        drop_frame.pack(fill=tk.X, padx=20, pady=10)

        self.file_label = ttk.Label(drop_frame, text="Drop a PDF here or click Choose", anchor="center")
        self.file_label.pack(fill=tk.X)

        if HAS_DND:
            drop_frame.drop_target_register(tkdnd.DND_FILES)
            drop_frame.dnd_bind("<<Drop>>", self._on_drop)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Choose PDF", command=self._pick_pdf).pack(side=tk.LEFT, padx=5)

        self.next_btn = ttk.Button(frame, text="Next", command=self._go_to_profile, state=tk.DISABLED)
        self.next_btn.pack(pady=10)

    def _on_drop(self, event: Any) -> None:
        path = event.data.strip("{}")
        if path.lower().endswith(".pdf"):
            self.pdf_path = path
            self.file_label.config(text=Path(path).name)
            self.next_btn.config(state=tk.NORMAL)

    def _pick_pdf(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.pdf_path = path
            self.file_label.config(text=Path(path).name)
            self.next_btn.config(state=tk.NORMAL)

    def _go_to_profile(self) -> None:
        self._load_profile_defaults()
        self._show_frame("profile")

    # -- Screen 2: Profile + Rules --

    def _build_profile_screen(self) -> None:
        frame = ttk.Frame(self.container)
        self.frames["profile"] = frame

        ttk.Label(frame, text="Profile & Rules", font=("", 14, "bold")).pack(pady=(10, 5))

        settings_frame = ttk.Frame(frame)
        settings_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(settings_frame, text="Profile:").grid(row=0, column=0, sticky="w", pady=2)
        self.profile_var = tk.StringVar(value="cmd_zuyd")
        profile_combo = ttk.Combobox(settings_frame, textvariable=self.profile_var, values=list_profiles(), state="readonly", width=25)
        profile_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        profile_combo.bind("<<ComboboxSelected>>", lambda e: self._load_profile_defaults())

        ttk.Label(settings_frame, text="Language:").grid(row=1, column=0, sticky="w", pady=2)
        self.lang_var = tk.StringVar(value="Auto")
        lang_combo = ttk.Combobox(settings_frame, textvariable=self.lang_var, values=["Auto", "English", "Nederlands"], state="readonly", width=25)
        lang_combo.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(settings_frame, text="Word limit:").grid(row=2, column=0, sticky="w", pady=2)
        limit_frame = ttk.Frame(settings_frame)
        limit_frame.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        ttk.Entry(limit_frame, textvariable=self.max_words_var, width=12).pack(side=tk.LEFT)
        ttk.Label(limit_frame, text="(0 = no limit)", foreground="gray").pack(side=tk.LEFT, padx=(5, 0))

        rules_frame = ttk.LabelFrame(frame, text="Rules", padding=10)
        rules_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        for i, rule_name in enumerate(RULE_LABELS):
            var = tk.BooleanVar()
            self.rule_vars[rule_name] = var
            cb = ttk.Checkbutton(rules_frame, text=RULE_LABELS[rule_name]["en"], variable=var)
            col = i % 2
            row = i // 2
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Back", command=lambda: self._show_frame("file")).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Analyze", command=self._run_analysis).pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(frame, text="")
        self.status_label.pack()

    def _load_profile_defaults(self) -> None:
        try:
            profile = load_profile(self.profile_var.get())
        except Exception:
            return
        rules = profile.rules
        for rule_name, var in self.rule_vars.items():
            var.set(getattr(rules, rule_name, False))
        self.max_words_var.set(str(profile.max_words) if profile.max_words > 0 else "")

    def _get_lang_override(self) -> str | None:
        val = self.lang_var.get()
        if val == "English":
            return "en"
        if val == "Nederlands":
            return "nl"
        return None

    def _run_analysis(self) -> None:
        if not self.pdf_path:
            messagebox.showerror("Error", "No PDF selected")
            return

        self.status_label.config(text="Analyzing...")

        def work() -> None:
            try:
                profile = load_profile(self.profile_var.get())
                # Apply rule overrides from checkboxes
                for rule_name, var in self.rule_vars.items():
                    if hasattr(profile.rules, rule_name):
                        setattr(profile.rules, rule_name, var.get())
                # Apply custom word limit
                try:
                    limit_str = self.max_words_var.get().strip()
                    profile.max_words = int(limit_str) if limit_str else 0
                except ValueError:
                    pass

                self.analyzed_profile = profile
                result = analyze(self.pdf_path, profile=profile, lang_override=self._get_lang_override())
                self.root.after(0, lambda: self._show_results(result))
            except Exception as e:
                self.root.after(0, lambda: self._show_error(str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _show_error(self, msg: str) -> None:
        self.status_label.config(text="")
        messagebox.showerror("Error", msg)

    def _show_results(self, result: AnalysisResult) -> None:
        self.result = result
        self.lang = result.language
        self.status_label.config(text="")
        self._populate_results()
        self._show_frame("results")

    # -- Screen 3: Results --

    def _build_results_screen(self) -> None:
        frame = ttk.Frame(self.container)
        self.frames["results"] = frame

        ttk.Label(frame, text="Results", font=("", 14, "bold")).pack(pady=(10, 5))

        self.summary_frame = ttk.LabelFrame(frame, text="Summary", padding=10)
        self.summary_frame.pack(fill=tk.X, padx=20, pady=5)

        self.summary_text = ttk.Label(self.summary_frame, text="", justify="left")
        self.summary_text.pack(fill=tk.X)

        self.progress_bar = ttk.Progressbar(self.summary_frame, length=300, mode="determinate")

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        cols = ("included", "level", "words", "status", "reasons")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)
        self.tree.heading("included", text="")
        self.tree.heading("level", text="Lvl")
        self.tree.heading("words", text="Words")
        self.tree.heading("status", text="Section")
        self.tree.heading("reasons", text="Reasons")
        self.tree.column("included", width=30, anchor="center")
        self.tree.column("level", width=40, anchor="center")
        self.tree.column("words", width=80, anchor="e")
        self.tree.column("status", width=200)
        self.tree.column("reasons", width=200)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Back", command=lambda: self._show_frame("profile")).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Export JSON", command=lambda: self._export("json")).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Export CSV", command=lambda: self._export("csv")).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Export Text", command=lambda: self._export("text")).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="New Analysis", command=self._reset).pack(side=tk.LEFT, padx=5)

    def _populate_results(self) -> None:
        if not self.result:
            return
        r = self.result
        total = r.total_included + r.total_excluded
        summary = f"{t('total_included', self.lang)}: {r.total_included:,}\n"
        summary += f"{t('total_excluded', self.lang)}: {r.total_excluded:,}\n"
        summary += f"{t('total_document', self.lang)}: {total:,}"

        profile = self.analyzed_profile or load_profile(r.profile_id)
        if profile.max_words > 0:
            pct = r.total_included / profile.max_words * 100
            status = t("within_limit", self.lang) if r.total_included <= profile.max_words else t("over_limit", self.lang)
            summary += f"\n{t('max_words', self.lang)}: {profile.max_words:,} ({pct:.1f}% - {status})"
            self.progress_bar.pack(fill=tk.X, pady=(5, 0))
            self.progress_bar["value"] = min(pct, 100)
        else:
            self.progress_bar.pack_forget()

        self.summary_text.config(text=summary)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for s in r.sections:
            mark = "V" if s.included else "X"
            count = s.word_count if s.included else s.excluded_word_count
            self.tree.insert("", tk.END, values=(
                mark,
                s.level,
                f"{count:,}",
                s.title,
                "; ".join(s.exclusion_reasons),
            ))

    def _export(self, fmt: str) -> None:
        if not self.result:
            return
        ext = {"json": "json", "csv": "csv", "text": "txt"}[fmt]
        default_name = generate_output_path(self.result.file_path, self.result.profile_id, ext)
        path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            initialfile=default_name,
            filetypes=[(f"{ext.upper()} files", f"*.{ext}")],
        )
        if not path:
            return
        if fmt == "json":
            export_json(self.result, path)
        elif fmt == "csv":
            export_csv(self.result, path)
        else:
            export_text(self.result, path, lang=self.lang)
        messagebox.showinfo("Export", f"Saved to {path}")

    def _reset(self) -> None:
        self.pdf_path = None
        self.result = None
        self.file_label.config(text="Drop a PDF here or click Choose")
        self.next_btn.config(state=tk.DISABLED)
        self._show_frame("file")

    def run(self) -> None:
        self.root.mainloop()


def launch_gui() -> None:
    app = ThesisCounterApp()
    app.run()
