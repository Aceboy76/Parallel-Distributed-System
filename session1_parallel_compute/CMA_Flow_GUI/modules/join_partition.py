from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .base import BaseModule


class JoinPartitionModule(BaseModule):
    def build(self, parent):
        frame = tk.Frame(parent, bg="#f3f6fa")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        join = tk.LabelFrame(
            frame, text=" Join & partition key ",
            bg="#f3f6fa", fg="#31455e",
            font=("Segoe UI", 9, "bold"), bd=0
        )
        join.pack(fill="x")

        self.app.join_path_var = tk.StringVar(
            value="assessments → customers_dim → assessment_defs → entitlements_dim"
        )
        tk.Label(
            join, textvariable=self.app.join_path_var,
            bg="#ffffff", fg="#24364b",
            font=("Consolas", 10), anchor="w",
            padx=12, pady=12
        ).pack(fill="x", padx=2, pady=2)

        self.app.join_detail_var = tk.StringVar(value="No join report yet.")
        tk.Label(
            join, textvariable=self.app.join_detail_var,
            bg="#f3f6fa", fg="#64748b",
            anchor="w", padx=8, pady=7
        ).pack(fill="x")

        strategy = tk.LabelFrame(
            frame, text=" Candidate partition keys ",
            bg="#f3f6fa", fg="#31455e",
            font=("Segoe UI", 9, "bold"), bd=0
        )
        strategy.pack(fill="both", expand=True, pady=(10, 0))

        columns = ("candidate", "source", "distinct", "min", "median", "max", "skew", "verdict")
        self.app.strategy_tree = ttk.Treeview(
            strategy, columns=columns, show="headings"
        )
        for c, title, width in [
            ("candidate", "Candidate", 160), ("source", "Source", 240),
            ("distinct", "Distinct", 85), ("min", "Min", 80),
            ("median", "Median", 90), ("max", "Max", 90),
            ("skew", "Skew", 85), ("verdict", "Verdict", 360)
        ]:
            self.app.strategy_tree.heading(c, text=title)
            self.app.strategy_tree.column(c, width=width, anchor="w")
        self.app.strategy_tree.pack(fill="both", expand=True, padx=6, pady=6)

        self.app.strategy_detail_var = tk.StringVar(value="")
        tk.Label(
            frame, textvariable=self.app.strategy_detail_var,
            bg="#ffffff", fg="#24364b",
            anchor="w", justify="left", padx=12, pady=10
        ).pack(fill="x", pady=(10, 0))

    def refresh(self):
        validation = self.load_json("validation_report.json")
        if validation:
            j = validation.get("join", {})
            self.app.join_detail_var.set(
                f"Rows: {j.get('rows_before', '—'):,} → "
                f"{j.get('rows_after', '—'):,}   •   Δ {j.get('delta', '—')}   •   "
                f"BroadcastHashJoin: {j.get('broadcast_hash_joins', '—')}   •   "
                f"SortMergeJoin: {j.get('sort_merge_joins', '—')}"
            )
        else:
            self.app.join_detail_var.set("No validation_report.json found yet.")

        self.clear_tree(self.app.strategy_tree)
        strategy = self.load_json("partition_strategy.json")
        if not strategy:
            self.app.strategy_detail_var.set(
                "Run Partition strategy to evaluate candidate keys."
            )
            return

        chosen = strategy.get("chosen_key", "—")
        pred = strategy.get("prediction", {})
        self.app.strategy_detail_var.set(
            f"Chosen key: {chosen}   •   owned by: {strategy.get('owned_by', '—')}   •   "
            f"{pred.get('distinct', '—')} distinct values   •   "
            f"predicted skew {pred.get('skew_ratio', '—')}:1   •   "
            f"join survival: {strategy.get('join_survival', {}).get('verdict', '—')}"
        )

        for item in strategy.get("all_candidates", []):
            verdict = "VIABLE" if item.get("viable") else item.get("rejected_because", "")
            self.app.strategy_tree.insert(
                "", "end",
                values=(
                    item.get("column", ""),
                    item.get("source_file", ""),
                    item.get("distinct", ""),
                    item.get("min", ""),
                    item.get("median", ""),
                    item.get("max", ""),
                    item.get("skew_ratio", ""),
                    verdict,
                )
            )
