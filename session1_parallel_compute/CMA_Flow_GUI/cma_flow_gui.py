"""
CMA-Flow — Session 1 Parallel Compute Console
Modular GUI built around the supplied Session 1 pipeline.

Run from the project root:
    python CMA_Flow_GUI\cma_flow_gui.py
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.widgets import WidgetFactory
from modules.pipeline import PipelineModule, STAGES
from modules.files_eligibility import FilesEligibilityModule
from modules.join_partition import JoinPartitionModule
from modules.baseline_parallel import BaselineParallelModule
from modules.correctness_output import CorrectnessOutputModule
from modules.partition_balance import PartitionBalanceModule
from modules.console import ConsoleModule
from modules.database import DatabaseModule


APP_TITLE = "CMA-Flow — Session 1 Parallel Compute Console"


class CMAFlowApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("1280x800")
        self.minsize(1080, 680)
        self.configure(bg="#f3f6fa")

        self.base_dir = __import__("pathlib").Path(PROJECT_ROOT)
        self.results_dir = self.base_dir / "results"
        self.data_dir = self.base_dir / "Datasets"

        self.proc = None
        self.worker = None
        self.events = queue.Queue()
        self.running_stage = None
        self.stage_status = {}
        self.db_connected = False

        self.widgets = WidgetFactory(self)
        self.widgets.setup_style()

        self.pipeline_module = PipelineModule(self)
        self.files_module = FilesEligibilityModule(self)
        self.join_module = JoinPartitionModule(self)
        self.baseline_module = BaselineParallelModule(self)
        self.correctness_module = CorrectnessOutputModule(self)
        self.partition_module = PartitionBalanceModule(self)
        self.console_module = ConsoleModule(self)
        self.db_module = DatabaseModule(self)

        self.build_header()
        self.build_tabs()
        self.refresh_all()

        self.after(100, self.poll_events)
        self.protocol("WM_DELETE_WINDOW", self.close_app)

    def build_header(self):
        header = tk.Frame(self, bg="#ffffff", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)

        left = tk.Frame(header, bg="#ffffff")
        left.pack(side="left", fill="both", expand=True, padx=18, pady=10)

        tk.Label(
            left,
            text="CMA-Flow — Session 1 Parallel Compute Console",
            bg="#ffffff", fg="#183153",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")

        tk.Label(
            left,
            text=(
                "MIT 261 Parallel and Distributed Systems  •  OULAD  •  "
                "partition key: region  •  bounded parallelism: 2 / 4 / 8"
            ),
            bg="#ffffff", fg="#6b7788",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(3, 0))

        right = tk.Frame(header, bg="#ffffff")
        right.pack(side="right", padx=16)

        ttk.Button(
            right, text="Run everything",
            command=self.pipeline_module.run_all
        ).pack(side="left", padx=4)

        ttk.Button(
            right, text="Refresh results",
            command=self.refresh_all
        ).pack(side="left", padx=4)

        ttk.Button(
            right, text="Database",
            command=self.show_database
        ).pack(side="left", padx=4)

        self.db_badge = tk.Label(
            right, text="DB: NOT CONNECTED",
            bg="#fde2e2", fg="#a12626",
            font=("Segoe UI", 8, "bold"),
            padx=10, pady=5,
        )
        self.db_badge.pack(side="left", padx=(4, 8))

        self.status_badge = tk.Label(
            right, text="READY",
            bg="#e8eef5", fg="#40556d",
            font=("Segoe UI", 9, "bold"),
            padx=12, pady=5,
        )
        self.status_badge.pack(side="left")

    def build_tabs(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        specs = [
            ("Pipeline", self.pipeline_module),
            ("Files & Eligibility", self.files_module),
            ("Join & Partition Key", self.join_module),
            ("Baseline vs Parallel", self.baseline_module),
            ("Correctness & Output", self.correctness_module),
            ("Partition Balance", self.partition_module),
            ("Console", self.console_module),
            ("Database", self.db_module),
        ]

        for title, module in specs:
            frame = tk.Frame(self.tabs, bg="#f3f6fa")
            self.tabs.add(frame, text=title)
            module.build(frame)

    def show_database(self):
        self.tabs.select(7)
        self.db_module.connect()

    def refresh_all(self):
        self.pipeline_module.refresh()
        self.files_module.refresh()
        self.join_module.refresh()
        self.baseline_module.refresh()
        self.correctness_module.refresh()
        self.partition_module.refresh()
        self.update_db_badge(self.db_connected)

    def update_db_badge(self, connected):
        if connected:
            self.db_badge.configure(
                text="DB: CONNECTED",
                bg="#dff4e5",
                fg="#21733a",
            )
        else:
            self.db_badge.configure(
                text="DB: NOT CONNECTED",
                bg="#fde2e2",
                fg="#a12626",
            )

    def db_query(self, sql, params=None, fetch=True):
        return self.db_module.query(sql, params, fetch)

    def clear_tree(self, tree):
        for item in tree.get_children():
            tree.delete(item)

    def console_write(self, text):
        self.console_module.write(text)

    def clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def open_project_folder(self):
        try:
            if sys.platform.startswith("win"):
                os.startfile(self.base_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.base_dir)])
            else:
                subprocess.Popen(["xdg-open", str(self.base_dir)])
        except Exception as exc:
            messagebox.showerror("Open project folder", str(exc), parent=self)

    def poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]

                if kind == "output":
                    self.console_write(event[1])
                    self.console_status.set("Process output received.")

                elif kind == "set_running":
                    name, script = event[1], event[2]
                    self.running_stage = script
                    self.stage_status[name] = "running"
                    self.status_badge.configure(
                        text="RUNNING", bg="#fff1c7", fg="#8a5a00"
                    )
                    self.run_all_btn_state(False)
                    self.pipeline_module.app.run_stage_btn.configure(state="disabled")
                    self.pipeline_module.app.stop_btn.configure(state="normal")
                    self.tabs.select(6)

                elif kind == "done":
                    name, script, rc = event[1], event[2], event[3]
                    self.running_stage = None
                    self.proc = None

                    if rc == 0:
                        self.stage_status[name] = "completed"
                        self.console_write(
                            f"\n[{script}] FINISHED successfully (exit {rc}).\n"
                        )
                    else:
                        self.stage_status[name] = "failed"
                        self.console_write(
                            f"\n[{script}] FAILED (exit {rc}).\n"
                        )

                    self.refresh_all()
                    self.run_all_btn_state(True)
                    self.pipeline_module.app.run_stage_btn.configure(state="normal")
                    self.pipeline_module.app.stop_btn.configure(state="disabled")

                    if rc != 0:
                        self.status_badge.configure(
                            text="FAILED", bg="#fde2e2", fg="#a12626"
                        )

                elif kind == "error":
                    name, script, exc = event[1], event[2], event[3]
                    self.running_stage = None
                    self.proc = None
                    self.stage_status[name] = "failed"
                    self.console_write(f"\n[ERROR] {script}: {exc}\n")
                    self.status_badge.configure(
                        text="FAILED", bg="#fde2e2", fg="#a12626"
                    )
                    self.run_all_btn_state(True)
                    self.pipeline_module.app.run_stage_btn.configure(state="normal")
                    self.pipeline_module.app.stop_btn.configure(state="disabled")
                    self.refresh_all()

                elif kind == "pipeline_failed":
                    script, rc, detail = event[1], event[2], event[3]
                    self.running_stage = None
                    self.proc = None
                    self.console_write(
                        f"\n[PIPELINE STOPPED] {script} returned exit code {rc}.\n"
                    )
                    if detail:
                        self.console_write(f"{detail}\n")
                    self.status_badge.configure(
                        text="FAILED", bg="#fde2e2", fg="#a12626"
                    )
                    self.run_all_btn_state(True)
                    self.pipeline_module.app.run_stage_btn.configure(state="normal")
                    self.pipeline_module.app.stop_btn.configure(state="disabled")
                    self.refresh_all()

                elif kind == "pipeline_done":
                    self.running_stage = None
                    self.proc = None
                    self.console_write(
                        "\n[RUN EVERYTHING] All stages completed successfully.\n"
                    )
                    self.status_badge.configure(
                        text="PASSED", bg="#dff4e5", fg="#21733a"
                    )
                    self.run_all_btn_state(True)
                    self.pipeline_module.app.run_stage_btn.configure(state="normal")
                    self.pipeline_module.app.stop_btn.configure(state="disabled")
                    self.refresh_all()

        except queue.Empty:
            pass

        self.after(100, self.poll_events)

    def run_all_btn_state(self, enabled):
        self.pipeline_module.app.run_all_btn.configure(
            state="normal" if enabled else "disabled"
        )

    def close_app(self):
        try:
            if self.proc is not None and self.proc.poll() is None:
                self.proc.terminate()
        except Exception:
            pass

        try:
            self.db_module.disconnect()
        except Exception:
            pass

        self.destroy()


if __name__ == "__main__":
    CMAFlowApp().mainloop()
