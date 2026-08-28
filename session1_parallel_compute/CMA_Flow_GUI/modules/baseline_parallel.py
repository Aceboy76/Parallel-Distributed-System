from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .base import BaseModule


class BaselineParallelModule(BaseModule):
    def build(self, parent):
        frame = tk.Frame(parent, bg="#f3f6fa")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        box = tk.LabelFrame(
            frame, text=" Baseline vs parallel ",
            bg="#f3f6fa", fg="#31455e",
            font=("Segoe UI", 9, "bold"), bd=0
        )
        box.pack(fill="both", expand=True)

        columns = ("run", "partitions", "time", "groups", "correct", "speedup", "observation")
        self.app.bench_tree = ttk.Treeview(box, columns=columns, show="headings")
        for c, title, width in [
            ("run", "Run", 210), ("partitions", "Partitions", 100),
            ("time", "Median (s)", 110), ("groups", "Groups", 80),
            ("correct", "Correct", 90), ("speedup", "Speedup", 100),
            ("observation", "Observation", 380)
        ]:
            self.app.bench_tree.heading(c, text=title)
            self.app.bench_tree.column(c, width=width, anchor="w")
        self.app.bench_tree.pack(fill="both", expand=True, padx=6, pady=6)

        self.app.benchmark_summary_var = tk.StringVar(
            value="Run Benchmark to generate session1_benchmark.csv."
        )
        tk.Label(
            frame, textvariable=self.app.benchmark_summary_var,
            bg="#ffffff", fg="#24364b",
            anchor="w", padx=12, pady=10
        ).pack(fill="x", pady=(10, 0))

    def refresh(self):
        self.clear_tree(self.app.bench_tree)
        rows = self.load_csv("session1_benchmark.csv")
        if not rows:
            self.app.benchmark_summary_var.set(
                "Run Benchmark to generate session1_benchmark.csv."
            )
            return

        for r in rows:
            self.app.bench_tree.insert(
                "", "end",
                values=(
                    r.get("run", ""),
                    r.get("parallelism_partitions", ""),
                    r.get("execution_time_s", ""),
                    r.get("groups", ""),
                    r.get("correct", ""),
                    r.get("speedup_vs_baseline", ""),
                    r.get("observation", ""),
                )
            )

        try:
            base = next(r for r in rows if r.get("run") == "Sequential baseline")
            parallel = [r for r in rows if r.get("run") != "Sequential baseline"]
            best = min(parallel, key=lambda r: float(r["execution_time_s"]))
            self.app.benchmark_summary_var.set(
                f"Baseline: {base.get('execution_time_s')} s   •   "
                f"Best parallel: {best.get('parallelism_partitions')} partitions at "
                f"{best.get('execution_time_s')} s   •   "
                f"speedup vs baseline: {best.get('speedup_vs_baseline')}x"
            )
        except Exception:
            pass
