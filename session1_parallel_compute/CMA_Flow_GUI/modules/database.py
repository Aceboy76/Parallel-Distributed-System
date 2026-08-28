from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox


class DatabaseModule:
    """GUI adapter for the project's database/db.py connection pool."""

    def __init__(self, app):
        self.app = app
        self.import_error = None
        try:
            from database.db import init_pool, get_conn, put_conn, is_ready
            self.init_pool = init_pool
            self.get_conn = get_conn
            self.put_conn = put_conn
            self.is_ready = is_ready
        except Exception as exc:
            self.import_error = exc
            self.init_pool = self.get_conn = self.put_conn = None
            self.is_ready = lambda: False

    def build(self, parent):
        frame = tk.Frame(parent, bg="#f3f6fa")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        header = tk.Frame(frame, bg="#f3f6fa")
        header.pack(fill="x")

        self.status_var = tk.StringVar(value="NOT CONNECTED")
        self.details_var = tk.StringVar(
            value="localhost:5432  •  cma_flow_db  •  postgres"
        )

        self.app.db_status_label = tk.Label(
            header, textvariable=self.status_var,
            bg="#fde2e2", fg="#a12626",
            font=("Segoe UI", 13, "bold"),
            padx=14, pady=10
        )
        self.app.db_status_label.pack(side="left")

        tk.Label(
            header, textvariable=self.details_var,
            bg="#ffffff", fg="#40556d",
            font=("Segoe UI", 9),
            anchor="w", padx=14, pady=10
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

        controls = tk.Frame(frame, bg="#f3f6fa")
        controls.pack(fill="x", pady=10)
        ttk.Button(controls, text="Connect",
                   command=self.connect).pack(side="left")
        ttk.Button(controls, text="Refresh tables",
                   command=self.refresh_tables).pack(side="left", padx=8)
        ttk.Button(controls, text="Test connection",
                   command=self.test_connection).pack(side="left")
        ttk.Button(controls, text="Disconnect",
                   command=self.disconnect).pack(side="left", padx=8)

        box = tk.LabelFrame(
            frame, text=" PostgreSQL public tables ",
            bg="#f3f6fa", fg="#31455e",
            font=("Segoe UI", 9, "bold"), bd=0
        )
        box.pack(fill="both", expand=True)

        self.table_tree = ttk.Treeview(
            box, columns=("schema", "table", "rows"), show="headings"
        )
        for c, title, width in [
            ("schema", "Schema", 160),
            ("table", "Table", 400),
            ("rows", "Rows", 140),
        ]:
            self.table_tree.heading(c, text=title)
            self.table_tree.column(c, width=width, anchor="w")
        self.table_tree.pack(fill="both", expand=True, padx=6, pady=6)

        self.message_var = tk.StringVar(value="")
        tk.Label(
            frame, textvariable=self.message_var,
            bg="#f3f6fa", fg="#64748b",
            anchor="w", padx=4, pady=6
        ).pack(fill="x")

    def connect(self):
        if self.import_error is not None:
            messagebox.showerror(
                "Database module error",
                f"Could not import database/db.py.\n\n{self.import_error}\n\n"
                "Install the driver with:\n"
                "pip install psycopg2-binary",
                parent=self.app,
            )
            return False

        password = os.getenv("CMA_DB_PASSWORD")
        if not password:
            password = simpledialog.askstring(
                "PostgreSQL Login",
                "PostgreSQL password for user 'postgres':",
                show="*",
                parent=self.app,
            )

        if password is None:
            self.app.console_write("\n[DATABASE] Connection cancelled.\n")
            return False

        try:
            # The supplied db.py intentionally ignores a second init when a
            # pool already exists. We close the old pool on failure below.
            self.init_pool(password)

            conn = self.get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT current_database(),
                               current_user,
                               COALESCE(inet_server_addr()::text, 'localhost'),
                               inet_server_port()
                        """
                    )
                    database, user, host, port = cur.fetchone()
            finally:
                self.put_conn(conn)

            self.app.db_connected = True
            self.status_var.set("CONNECTED")
            self.details_var.set(f"{database}  •  {user}  •  {host}:{port}")
            self.message_var.set("PostgreSQL connection established.")
            self.app.update_db_badge(True)

            self.app.console_write(
                "\n[DATABASE] CONNECTED\n"
                f"Database: {database}\n"
                f"User:     {user}\n"
                f"Server:   {host}:{port}\n"
            )
            self.refresh_tables()
            return True

        except Exception as exc:
            self.app.db_connected = False
            self.status_var.set("NOT CONNECTED")
            self.details_var.set(str(exc))
            self.message_var.set(f"Connection failed: {exc}")
            self.app.update_db_badge(False)
            self.app.console_write(
                f"\n[DATABASE] CONNECTION FAILED\n"
                f"{type(exc).__name__}: {exc}\n"
            )
            messagebox.showerror(
                "Database connection failed",
                f"{type(exc).__name__}: {exc}\n\n"
                "Expected connection:\n"
                "Host: localhost\nPort: 5432\n"
                "Database: cma_flow_db\nUser: postgres",
                parent=self.app,
            )
            return False

    def query(self, sql, params=None, fetch=True):
        if not self.app.db_connected or not self.is_ready():
            raise RuntimeError(
                "Database is not connected. Click Database and connect first."
            )

        conn = self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if fetch:
                    return cur.fetchall()
                conn.commit()
                return None
        except Exception:
            conn.rollback()
            raise
        finally:
            self.put_conn(conn)

    def refresh_tables(self):
        if not self.app.db_connected or not self.is_ready():
            return

        self.app.clear_tree(self.table_tree)

        try:
            tables = self.query(
                """
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            )

            conn = self.get_conn()
            try:
                with conn.cursor() as cur:
                    for schema, table in tables:
                        try:
                            # Identifiers come from information_schema, not
                            # user input, so quoting them is safe here.
                            cur.execute(
                                f'SELECT COUNT(*) FROM "{schema}"."{table}"'
                            )
                            count = cur.fetchone()[0]
                        except Exception:
                            conn.rollback()
                            count = "?"
                        self.table_tree.insert(
                            "", "end", values=(schema, table, count)
                        )
            finally:
                self.put_conn(conn)

            self.message_var.set(f"{len(tables)} public table(s) found.")
        except Exception as exc:
            self.message_var.set(f"Could not read tables: {exc}")

    def test_connection(self):
        try:
            database, user, version = self.query(
                "SELECT current_database(), current_user, version()"
            )[0]
            self.app.console_write(
                "\n[DATABASE TEST] SUCCESS\n"
                f"Database: {database}\n"
                f"User: {user}\n"
                f"PostgreSQL: {version.splitlines()[0]}\n"
            )
            return True
        except Exception as exc:
            self.app.console_write(
                f"\n[DATABASE TEST] FAILED: {type(exc).__name__}: {exc}\n"
            )
            return False

    def disconnect(self):
        try:
            import database.db as db
            if getattr(db, "_pool", None) is not None:
                db._pool.closeall()
                db._pool = None
        except Exception:
            pass

        self.app.db_connected = False
        self.status_var.set("NOT CONNECTED")
        self.details_var.set(
            "localhost:5432  •  cma_flow_db  •  postgres"
        )
        self.message_var.set("Disconnected.")
        self.app.update_db_badge(False)
