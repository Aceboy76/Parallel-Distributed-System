from PyQt6.QtWidgets import QVBoxLayout,QPlainTextEdit
from .base import BaseModule
class ConsoleModule(BaseModule):
 def build(self,w):
  lay=self.shell(w); self.console=QPlainTextEdit(); self.console.setReadOnly(True); self.console.setStyleSheet('background:#102a4d;color:#e6edf6;font-family:Consolas;font-size:12px;'); lay.addWidget(self.console,1)
 def write(self,text): self.console.appendPlainText(text)
