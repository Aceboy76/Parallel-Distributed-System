from __future__ import annotations

import csv
import json


class BaseModule:
    def __init__(self, app):
        self.app = app

    @property
    def base_dir(self):
        return self.app.base_dir

    @property
    def results_dir(self):
        return self.app.results_dir

    @property
    def data_dir(self):
        return self.app.data_dir

    def load_json(self, filename):
        path = self.results_dir / filename
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def load_csv(self, filename):
        path = self.results_dir / filename
        if not path.exists():
            return None
        try:
            with path.open(newline="", encoding="utf-8") as fh:
                return list(csv.DictReader(fh))
        except Exception:
            return None

    @staticmethod
    def clear_tree(tree):
        for item in tree.get_children():
            tree.delete(item)
