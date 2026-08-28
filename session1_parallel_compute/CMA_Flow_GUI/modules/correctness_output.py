from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .base import BaseModule


class CorrectnessOutputModule(BaseModule):
    def build(self, parent):
        frame = tk.Frame(parent, bg="#f3f6fa")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        check = tk.LabelFrame(
            frame, text=" Correctness ",
            bg="#f3f6fa", fg="#31455e",
            font=("Segoe UI", 9, "bold"), bd=0
        )
        check.pack(fill="x")

        self.app.correctness_var = tk.StringVar(value="No validation report.")
        tk.Label(
            check, textvariable=self.app.correctness_var,
            bg="#ffffff", fg="#183153",
            font=("Segoe UI", 13, "bold"),
            anchor="w", padx=14, pady=12
        ).pack(fill="x")

        columns = ("metric", "value")
        self.app.validation_tree = ttk.Treeview(
            check, columns=columns, show="headings", height=8
        )
        self.app.validation_tree.heading("metric", text="Validation metric")
        self.app.validation_tree.heading("value", text="Value")
        self.app.validation_tree.column("metric", width=360)
        self.app.validation_tree.column("value", width=650)
        self.app.validation_tree.pack(fill="x", padx=6, pady=6)

        out = tk.LabelFrame(
            frame, text=" Results artifacts ",
            bg="#f3f6fa", fg="#31455e",
            font=("Segoe UI", 9, "bold"), bd=0
        )
        out.pack(fill="both", expand=True, pady=(10, 0))

        self.app.output_tree = ttk.Treeview(
            out, columns=("artifact", "status", "size", "modified"),
            show="headings"
        )
        for c, title, width in [
            ("artifact", "Artifact", 320), ("status", "Status", 110),
            ("size", "Size", 120), ("modified", "Last written", 180)
        ]:
            self.app.output_tree.heading(c, text=title)
            self.app.output_tree.column(c, width=width, anchor="w")
        self.app.output_tree.pack(fill="both", expand=True, padx=6, pady=6)

    def refresh(self):
        self.clear_tree(self.app.validation_tree)
        self.clear_tree(self.app.output_tree)

        report = self.load_json("validation_report.json")
        if report:
            v = report.get("validation", {})
            passed = v.get("passed")
            self.app.correctness_var.set(
                f"VALIDATION {'PASSED' if passed else 'FAILED'}"
            )
            for section, values in report.items():
                if isinstance(values, dict):
                    for key, value in values.items():
                        if isinstance(value, (str, int, float, bool)):
                            self.app.validation_tree.insert(
                                "", "end",
                                values=(f"{section}.{key}", value)
                            )
        else:
            self.app.correctness_var.set(
                "No validation_report.json found. Run Parallel compute."
            )

        artifacts = [
            "file_profile.json",
            "prep_report.json",
            "working_dataset.parquet",
            "partition_strategy.json",
            "baseline_result.csv",
            "regional_score_summary.parquet",
            "validation_report.json",
            "session1_benchmark.csv",
            "partition_sizes.csv",
        ]

        for name in artifacts:
            path = self.results_dir / name
            if path.exists():
                stat = path.stat()
                size = (
                    f"{stat.st_size / 1024:,.1f} KB"
                    if stat.st_size < 1024 * 1024
                    else f"{stat.st_size / (1024 * 1024):,.2f} MB"
                )
                modified = __import__("datetime").datetime.fromtimestamp(
                    stat.st_mtime
                ).strftime("%Y-%m-%d %H:%M:%S")
                status = "written"
            else:
                size, modified, status = "—", "—", "missing"

            self.app.output_tree.insert(
                "", "end", values=(name, status, size, modified)
            )
