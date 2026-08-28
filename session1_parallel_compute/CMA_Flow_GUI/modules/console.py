from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ConsoleModule:
    def __init__(self, app):
        self.app = app

    def build(self, parent):
        frame = tk.Frame(parent, bg="#111827")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        toolbar = tk.Frame(frame, bg="#111827")
        toolbar.pack(fill="x", padx=8, pady=8)

        ttk.Button(toolbar, text="Clear",
                   command=self.app.clear_console).pack(side="left")
        ttk.Button(toolbar, text="Stop process",
                   command=self.app.pipeline_module.stop).pack(side="left", padx=8)
        ttk.Button(toolbar, text="Test database",
                   command=self.app.db_module.test_connection).pack(side="left", padx=8)

        self.app.console_status = tk.StringVar(value="Console ready.")
        tk.Label(
            toolbar, textvariable=self.app.console_status,
            bg="#111827", fg="#9ca3af",
            font=("Segoe UI", 9)
        ).pack(side="left", padx=8)

        self.app.console = tk.Text(
            frame, bg="#0b1220", fg="#d7e0ea",
            insertbackground="#ffffff",
            font=("Consolas", 9),
            relief="flat", wrap="none"
        )
        self.app.console.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.app.console.configure(state="disabled")

    def write(self, text):
        self.app.console.configure(state="normal")
        self.app.console.insert("end", text)
        self.app.console.see("end")
        self.app.console.configure(state="disabled")
