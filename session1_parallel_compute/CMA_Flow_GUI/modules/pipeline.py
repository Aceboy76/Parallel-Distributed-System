from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from .base import BaseModule


STAGES = [
    ("1. Profile files", "profile_files.py", "Profile input files and eligibility conditions"),
    ("2. Load and join", "load_and_join.py", "Build the joined working dataset"),
    ("3. Partition strategy", "partition_strategy.py", "Evaluate partition-key candidates"),
    ("4. Sequential baseline", "sequential_baseline.py", "Create the pandas reference result"),
    ("5. Parallel compute", "parallel_compute.py", "Run Spark aggregation and correctness validation"),
    ("6. Benchmark", "benchmark.py", "Compare pandas against Spark at 2, 4, and 8 partitions"),
    ("7. Partition balance", "partition_analysis.py", "Measure key-level and physical Spark-partition skew"),
    ("8. Render diagrams", "render_diagrams.py", "Generate the architecture and entity diagrams"),
]


class PipelineModule(BaseModule):
    def build(self, parent):
        top = tk.Frame(parent, bg="#f3f6fa")
        top.pack(fill="x", padx=10, pady=10)

        self.app.rows_var = self.app.widgets.card(
            top, "Rows through the join", "—", "joined working dataset", 0
        )
        self.app.groups_var = self.app.widgets.card(
            top, "Groups in result", "—", "regional aggregates", 1
        )
        self.app.parts_var = self.app.widgets.card(
            top, "Partitions", "—", "configured final Spark run", 2
        )
        self.app.pass_var = self.app.widgets.card(
            top, "Validation", "—", "baseline comparison", 3
        )

        box = tk.LabelFrame(
            parent, text=" Run a stage ", bg="#f3f6fa",
            fg="#31455e", font=("Segoe UI", 9, "bold"), bd=0
        )
        box.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        columns = ("stage", "engine", "status", "headline")
        self.app.stage_tree = ttk.Treeview(box, columns=columns, show="headings")
        for c, title, width in [
            ("stage", "Stage", 210), ("engine", "Engine", 90),
            ("status", "Status", 100), ("headline", "Headline result", 680)
        ]:
            self.app.stage_tree.heading(c, text=title)
            self.app.stage_tree.column(c, width=width, anchor="w")

        scroll = ttk.Scrollbar(box, orient="vertical",
                               command=self.app.stage_tree.yview)
        self.app.stage_tree.configure(yscrollcommand=scroll.set)
        self.app.stage_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.app.stage_tree.bind("<Double-1>", self.run_selected)

        controls = tk.Frame(parent, bg="#f3f6fa")
        controls.pack(fill="x", padx=10, pady=(0, 10))

        self.app.run_stage_btn = ttk.Button(
            controls, text="Run selected stage", command=self.run_selected
        )
        self.app.run_stage_btn.pack(side="left")

        self.app.run_all_btn = ttk.Button(
            controls, text="Run everything", command=self.run_all
        )
        self.app.run_all_btn.pack(side="left", padx=8)

        ttk.Button(
            controls, text="Refresh from results",
            command=self.app.refresh_all
        ).pack(side="left")

        ttk.Button(
            controls, text="Open project folder",
            command=self.app.open_project_folder
        ).pack(side="left", padx=8)

        self.app.stop_btn = ttk.Button(
            controls, text="Stop", command=self.stop,
            state="disabled"
        )
        self.app.stop_btn.pack(side="left")

    def refresh(self):
        tree = self.app.stage_tree
        self.clear_tree(tree)

        validation = self.load_json("validation_report.json")
        strategy = self.load_json("partition_strategy.json")

        if validation:
            join = validation.get("join", {})
            agg = validation.get("aggregation", {})
            val = validation.get("validation", {})
            rows = join.get("rows_after")
            self.app.rows_var.set(f"{rows:,}" if isinstance(rows, int) else "—")
            self.app.groups_var.set(str(agg.get("groups", "—")))
            self.app.parts_var.set(str(agg.get("partitions", "—")))
            self.app.pass_var.set("PASSED" if val.get("passed") else "FAILED")
        else:
            for var in (
                self.app.rows_var, self.app.groups_var,
                self.app.parts_var, self.app.pass_var
            ):
                var.set("—")

        for i, (name, script, _desc) in enumerate(STAGES):
            engine = self.engine_for(script)
            self.app.stage_tree.insert(
                "", "end", iid=str(i),
                values=(name, engine, self.stage_status(name, script),
                        self.stage_headline(script))
            )

        if strategy:
            pred = strategy.get("prediction", {})
            self.app.partition_summary_var.set(
                f"Chosen key: {strategy.get('chosen_key', '—')}   •   "
                f"{pred.get('distinct', '—')} distinct values   •   "
                f"predicted skew {pred.get('skew_ratio', '—')}:1"
            )

    @staticmethod
    def engine_for(script):
        if script in {"parallel_compute.py", "benchmark.py", "partition_analysis.py"}:
            return "Spark"
        if script == "sequential_baseline.py":
            return "pandas"
        return "Python"

    def stage_status(self, name, script):
        if self.app.running_stage == script:
            return "running"
        if self.app.stage_status.get(name) == "completed":
            return "completed"
        if self.app.stage_status.get(name) == "failed":
            return "failed"

        expected = {
            "profile_files.py": "file_profile.json",
            "load_and_join.py": "working_dataset.parquet",
            "partition_strategy.py": "partition_strategy.json",
            "sequential_baseline.py": "baseline_result.csv",
            "parallel_compute.py": "validation_report.json",
            "benchmark.py": "session1_benchmark.csv",
            "partition_analysis.py": "partition_sizes.csv",
        }
        artifact = expected.get(script)
        if artifact and (self.results_dir / artifact).exists():
            return "completed"

        if script == "render_diagrams.py":
            if (
                (self.base_dir / "docs" / "entity-model-session1.png").exists()
                or (self.base_dir / "architecture" / "architecture-session1.png").exists()
            ):
                return "completed"
        return "not run"

    def stage_headline(self, script):
        if script == "profile_files.py":
            p = self.load_json("file_profile.json")
            if p:
                e = p.get("eligibility", {})
                rows = e.get("condition_4_volume", {}).get("event_rows", 0)
                met = sum(
                    1 for v in e.values()
                    if isinstance(v, dict) and v.get("met") is True
                )
                return f"{rows:,} event rows • {met}/4 eligibility conditions met"

        if script == "load_and_join.py":
            p = self.load_json("validation_report.json")
            if p:
                j = p.get("join", {})
                return (
                    f"{j.get('rows_before', 0):,} → {j.get('rows_after', 0):,} rows • "
                    f"Δ {j.get('delta', 0)} • {j.get('columns_after', '—')} columns"
                )

        if script == "partition_strategy.py":
            p = self.load_json("partition_strategy.json")
            if p:
                pred = p.get("prediction", {})
                return (
                    f"chosen {p.get('chosen_key', '—')} • "
                    f"{pred.get('distinct', '—')} distinct • "
                    f"skew {pred.get('skew_ratio', '—')}:1"
                )

        if script == "sequential_baseline.py":
            rows = self.load_csv("baseline_result.csv")
            return (
                f"{len(rows):,} regional groups"
                if rows is not None else "Create pandas correctness reference"
            )

        if script == "parallel_compute.py":
            p = self.load_json("validation_report.json")
            if p:
                v = p.get("validation", {})
                a = p.get("aggregation", {})
                return (
                    f"{v.get('parallel_groups', '—')} groups • "
                    f"{a.get('seconds', '—')} s • "
                    f"correctness {'PASSED' if v.get('passed') else 'FAILED'}"
                )

        if script == "benchmark.py":
            rows = self.load_csv("session1_benchmark.csv")
            if rows:
                try:
                    parallel = [
                        r for r in rows
                        if r.get("run") != "Sequential baseline"
                    ]
                    best = min(
                        parallel,
                        key=lambda r: float(r["execution_time_s"])
                    )
                    return (
                        f"best parallel setting: "
                        f"{best.get('parallelism_partitions')} partitions • "
                        f"{best.get('execution_time_s')} s • "
                        f"{best.get('speedup_vs_baseline')}x vs baseline"
                    )
                except Exception:
                    pass

        if script == "partition_analysis.py":
            return (
                "key-level + physical partition measurements available"
                if (self.results_dir / "partition_sizes.csv").exists()
                else "Measure partition skew"
            )

        if script == "render_diagrams.py":
            return "diagram artifacts found"

        return ""

    def selected_stage(self):
        selected = self.app.stage_tree.selection()
        if not selected:
            return None
        return STAGES[int(selected[0])]

    def run_selected(self, _event=None):
        stage = self.selected_stage()
        if stage:
            self.start_jobs([stage])

    def run_all(self):
        stages = [
            ("Preparation", "prep_oulad.py", "Build prepared dimension files"),
            *STAGES,
        ]
        self.start_jobs(stages)

    def start_jobs(self, jobs):
        if self.app.worker and self.app.worker.is_alive():
            messagebox.showwarning(
                "Pipeline busy",
                "A pipeline job is already running.",
                parent=self.app,
            )
            return

        self.app.worker = threading.Thread(
            target=self.worker_run,
            args=(jobs,),
            daemon=True,
        )
        self.app.worker.start()

    def worker_run(self, jobs):
        for name, script, _desc in jobs:
            script_path = self.base_dir / script
            if not script_path.exists():
                self.app.events.put(("pipeline_failed", script, 1,
                                     f"Missing script: {script_path}"))
                return

            self.app.events.put(("set_running", name, script))
            rc = self.execute_one(name, script)

            if rc != 0:
                self.app.events.put(("pipeline_failed", script, rc, None))
                return

        self.app.events.put(("pipeline_done",))

    def execute_one(self, name, script):
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        proc = None
        try:
            proc = subprocess.Popen(
                [sys.executable, script],
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
            )
            self.app.proc = proc

            self.app.events.put((
                "output",
                f"\n{'=' * 78}\n"
                f"START  {name}\n"
                f"Command: {sys.executable} {script}\n"
                f"{'=' * 78}\n"
            ))

            if proc.stdout is not None:
                for line in iter(proc.stdout.readline, ""):
                    self.app.events.put(("output", line))

            rc = proc.wait()
            self.app.events.put(("done", name, script, rc))
            return rc

        except Exception as exc:
            self.app.events.put(("error", name, script, repr(exc)))
            return 1
        finally:
            # Do not clear this from the worker. The UI event handler owns
            # app.proc, which prevents the old NoneType/.wait() race.
            pass

    def stop(self):
        proc = self.app.proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                self.app.events.put(("output", "\n[STOP] Termination requested.\n"))
            except Exception as exc:
                self.app.events.put(("output", f"\n[STOP ERROR] {exc}\n"))
