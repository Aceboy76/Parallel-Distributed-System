from PyQt6.QtWidgets import QVBoxLayout,QHBoxLayout,QPushButton,QWidget,QLabel
from .widgets import WidgetFactory
class BaseModule:
    def __init__(self,app): self.app=app; self.widgets=WidgetFactory(app)
    def shell(self,w):
        lay=QVBoxLayout(w); lay.setContentsMargins(22,18,22,14); lay.setSpacing(12); return lay
    def button(self,text,fn,primary=False):
        b=QPushButton(text); b.clicked.connect(fn)
        if primary:b.setObjectName('primary')
        return b
