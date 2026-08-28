from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .base import BaseModule


class PartitionBalanceModule(BaseModule):
    def build(self, parent):
        frame = tk.Frame(parent, bg="#f3f6fa")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.app.partition_summary_var = tk.StringVar(
            value="Partition analysis not loaded."
        )
        tk.Label(
            frame, textvariable=self.app.partition_summary_var,
            bg="#ffffff", fg="#183153",
            font=("Segoe UI", 13, "bold"),
            anchor="w", padx=14, pady=10
        ).pack(fill="x")

        columns = ("level", "setting", "identifier", "count", "even", "vs_even")
        self.app.part_tree = ttk.Treeview(
            frame, columns=columns, show="headings"
        )
        for c, title, width in [
            ("level", "Level", 160), ("setting", "Setting", 90),
            ("identifier", "Identifier", 270), ("count", "Records", 110),
            ("even", "Even share", 110), ("vs_even", "Vs even", 100)
        ]:
            self.app.part_tree.heading(c, text=title)
            self.app.part_tree.column(c, width=width, anchor="w")
        self.app.part_tree.pack(fill="both", expand=True, pady=(8, 0))

        self.app.partition_note_var = tk.StringVar(value="")
        tk.Label(
            frame, textvariable=self.app.partition_note_var,
            bg="#f3f6fa", fg="#64748b",
            anchor="w", justify="left", padx=4, pady=8
        ).pack(fill="x")

    def refresh(self):
        self.clear_tree(self.app.part_tree)
        path = self.results_dir / "partition_sizes.csv"
        if not path.exists():
            self.app.partition_note_var.set(
                "Run Partition balance to generate partition_sizes.csv."
            )
            return

        try:
            import csv
            with path.open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))

            for r in rows:
                self.app.part_tree.insert(
                    "", "end",
                    values=(
                        r.get("level", ""),
                        r.get("setting", ""),
                        r.get("identifier", ""),
                        f"{int(float(r.get('record_count', 0))):,}",
                        f"{float(r.get('even_share', 0)):,.1f}",
                        f"{float(r.get('vs_even', 0)):.3f}x",
                    )
                )

            key_rows = [r for r in rows if r.get("level") == "partition_key"]
            spark_rows = [r for r in rows if r.get("level") == "spark_partition"]

            if key_rows:
                max_ratio = max(float(r["vs_even"]) for r in key_rows)
                min_ratio = min(float(r["vs_even"]) for r in key_rows)
                self.app.partition_note_var.set(
                    f"Region key-level range: {min_ratio:.3f}x to {max_ratio:.3f}x "
                    f"of even share   •   "
                    f"{len(spark_rows)} physical Spark-partition records loaded."
                )
        except Exception as exc:
            self.app.partition_note_var.set(f"Could not read partition sizes: {exc}")
