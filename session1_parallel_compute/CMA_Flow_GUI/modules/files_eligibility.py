from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .base import BaseModule


class FilesEligibilityModule(BaseModule):
    FILES = [
        ("assessments", "studentAssessment.csv", "Event"),
        ("customers", "customers_dim.csv", "Entity"),
        ("entitlements", "entitlements_dim.csv", "Entity"),
        ("assessment_configs", "assessment_defs.csv", "Lookup"),
    ]

    def build(self, parent):
        frame = tk.Frame(parent, bg="#f3f6fa")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        box = tk.LabelFrame(
            frame, text=" Files & eligibility ",
            bg="#f3f6fa", fg="#31455e",
            font=("Segoe UI", 9, "bold"), bd=0
        )
        box.pack(fill="both", expand=True)

        columns = ("file", "role", "rows", "columns", "size", "status")
        self.app.file_tree = ttk.Treeview(box, columns=columns, show="headings")
        for c, title, width in [
            ("file", "File", 280), ("role", "Role", 100), ("rows", "Rows", 110),
            ("columns", "Columns", 90), ("size", "Size", 110), ("status", "Status", 120)
        ]:
            self.app.file_tree.heading(c, text=title)
            self.app.file_tree.column(c, width=width, anchor="w")
        self.app.file_tree.pack(fill="both", expand=True, padx=6, pady=6)

        self.app.eligibility_var = tk.StringVar(
            value="Run Profile files to load eligibility results."
        )
        tk.Label(
            frame, textvariable=self.app.eligibility_var,
            bg="#ffffff", fg="#24364b",
            anchor="w", justify="left", padx=12, pady=10
        ).pack(fill="x", pady=(10, 0))

        self.app.integrity_var = tk.StringVar(value="")
        tk.Label(
            frame, textvariable=self.app.integrity_var,
            bg="#f3f6fa", fg="#64748b",
            anchor="w", justify="left", padx=4, pady=7
        ).pack(fill="x")

    def refresh(self):
        self.clear_tree(self.app.file_tree)
        profile = self.load_json("file_profile.json")
        profiles = profile.get("profiles", {}) if profile else {}

        for key, filename, role in self.FILES:
            path = self.data_dir / filename
            meta = profiles.get(key, {})
            rows = meta.get("rows", "—")
            cols = meta.get("columns", "—")
            if meta.get("size_kb"):
                size = f"{meta['size_kb']:,.1f} KB"
            elif path.exists():
                size = f"{path.stat().st_size / 1024:,.1f} KB"
            else:
                size = "—"
            status = "loaded" if path.exists() else "missing"
            self.app.file_tree.insert(
                "", "end",
                values=(filename, role, rows, cols, size, status)
            )

        if not profile:
            self.app.eligibility_var.set(
                "Run Profile files to load eligibility results."
            )
            self.app.integrity_var.set("")
            return

        e = profile.get("eligibility", {})
        labels = [
            ("condition_1_three_related_files", "3 related files"),
            ("condition_2_one_to_many", "one-to-many"),
            ("condition_3_timestamp", "timestamp"),
            ("condition_4_volume", "volume"),
        ]
        parts = []
        for key, label in labels:
            met = e.get(key, {}).get("met")
            parts.append(f"{label}: {'PASSED' if met else 'FAILED'}")
        self.app.eligibility_var.set("  •  ".join(parts))

        integrity = profile.get("integrity", {}).get("foreign_keys_resolve", {})
        if integrity:
            bad = [k for k, v in integrity.items() if not v]
            self.app.integrity_var.set(
                "Foreign-key integrity: PASSED"
                if not bad else
                "Foreign-key integrity FAILED: " + ", ".join(bad)
            )
