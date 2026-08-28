from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class WidgetFactory:
    def __init__(self, app):
        self.app = app

    def setup_style(self):
        style = ttk.Style(self.app)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TNotebook", background="#f3f6fa", borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(15, 8),
            font=("Segoe UI", 9, "bold"),
            background="#e7edf4",
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#ffffff")],
            foreground=[("selected", "#183153")],
        )
        style.configure(
            "Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#233044",
            rowheight=27,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background="#233f70",
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
        )
        style.map("Treeview", background=[("selected", "#dbeafe")])
        style.configure(
            "TButton",
            padding=(10, 6),
            font=("Segoe UI", 9, "bold"),
        )

    def card(self, parent, title, value, subtitle, column):
        frame = tk.Frame(parent, bg="#ffffff", bd=1, relief="solid")
        frame.grid(row=0, column=column, sticky="nsew", padx=5)
        tk.Label(
            frame, text=title.upper(), bg="#ffffff", fg="#65758a",
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", padx=14, pady=(10, 0))
        var = tk.StringVar(value=value)
        tk.Label(
            frame, textvariable=var, bg="#ffffff", fg="#183153",
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", padx=14, pady=(2, 0))
        tk.Label(
            frame, text=subtitle, bg="#ffffff", fg="#7b8796",
            font=("Segoe UI", 8)
        ).pack(anchor="w", padx=14, pady=(0, 10))
        parent.grid_columnconfigure(column, weight=1)
        return var
