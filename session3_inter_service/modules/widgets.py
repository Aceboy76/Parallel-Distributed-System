from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PyQt6.QtWidgets import QFrame,QLabel,QPushButton,QTableWidget,QSizePolicy,QHeaderView,QVBoxLayout,QWidget
BG='#f7f9fc'; SURFACE='#ffffff'; NAVY='#223f73'; NAVY_2='#102a4d'; TEXT='#18304f'; MUTED='#6c7f98'; BORDER='#cbd6e3'; SUCCESS='#54833a'; SUCCESS_BG='#e4f1da'; WARNING='#c46a00'; WARNING_BG='#fde4d0'; DANGER='#b73b4a'; DANGER_BG='#f8e4e7'; BLUE_BG='#edf3fa'

def apply_table(t, compact=False):
    t.setShowGrid(False); t.setAlternatingRowColors(False); t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); t.verticalHeader().setVisible(False); t.setWordWrap(False)
    t.setStyleSheet(f'''QTableWidget{{background:white;color:{TEXT};border:1px solid #b8c2ce;font-size:13px;outline:none;}} QHeaderView::section{{background:{NAVY};color:white;border:0;padding:7px 8px;font-weight:700;font-size:13px;}} QTableWidget::item{{padding:{6 if compact else 8}px 7px;border:0;}} QTableWidget::item:selected{{background:#dbe8f7;color:{NAVY_2};}} QScrollBar:vertical{{width:12px;background:#eef2f6;}} QScrollBar::handle:vertical{{background:#aeb9c6;min-height:26px;}}''')
    t.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)

def card(layout,value,subtitle,accent=NAVY):
    f=QFrame(); f.setStyleSheet(f'QFrame{{background:{BLUE_BG};border:1px solid #c7d7ea;}}'); v=QVBoxLayout(f); v.setContentsMargins(10,14,10,10); v.setSpacing(2)
    x=QLabel(value); x.setAlignment(Qt.AlignmentFlag.AlignCenter); x.setStyleSheet(f'color:{accent};font-family:Georgia;font-size:30px;font-weight:800;border:0;'); v.addWidget(x)
    s=QLabel(subtitle); s.setAlignment(Qt.AlignmentFlag.AlignCenter); s.setStyleSheet(f'color:{MUTED};font-size:12px;border:0;'); v.addWidget(s); layout.addWidget(f,1); return x

class BarChart(QWidget):
    def __init__(self, bars=None, y_title='', parent=None):
        super().__init__(parent); self.bars=bars or []; self.y_title=y_title; self.setMinimumHeight(245); self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
    def set_data(self,bars,y_title=''):
        self.bars=bars or []; self.y_title=y_title; self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); r=self.rect(); p.fillRect(r,QBrush(QColor('white')))
        if not self.bars:return
        left,right,top,bottom=62,20,18,52; chart_w=max(1,r.width()-left-right); chart_h=max(1,r.height()-top-bottom); maxv=max(float(v) for _,v in self.bars) or 1
        p.setPen(QPen(QColor('#d7e0ea'))); p.drawLine(left,top,left,r.height()-bottom); p.drawLine(left,r.height()-bottom,r.width()-right,r.height()-bottom)
        font=QFont('Segoe UI',9); p.setFont(font)
        n=len(self.bars); gap=max(8,chart_w//(n*5)); bw=max(16,(chart_w-gap*(n+1))//n)
        for i,(label,val) in enumerate(self.bars):
            val=float(val); h=chart_h*val/maxv; x=left+gap+i*(bw+gap); y=top+chart_h-h
            p.setBrush(QBrush(QColor('#347bb5'))); p.setPen(Qt.PenStyle.NoPen); p.drawRect(x,int(y),bw,int(h))
            p.setPen(QPen(QColor(NAVY_2))); p.drawText(x, max(12,int(y)-5), bw,18,Qt.AlignmentFlag.AlignCenter,f'{val:g}')
            p.drawText(x,r.height()-bottom+7,bw,35,Qt.AlignmentFlag.AlignCenter,str(label))
        p.setPen(QPen(QColor(MUTED))); p.drawText(8,top,48,20,Qt.AlignmentFlag.AlignRight,self.y_title)

class WidgetFactory:
    def __init__(self,app): self.app=app
    def card(self,layout,value,subtitle,accent=NAVY): return card(layout,value,subtitle,accent)
    def setup_style(self):
        self.app.setStyleSheet(f'''QWidget{{font-family:"Segoe UI";color:{TEXT};}} QMainWindow{{background:{BG};}} QPushButton{{background:#f4f7fb;color:#294a72;border:0;padding:9px 14px;font-size:13px;}} QPushButton:hover{{background:#e8eff8;}} QPushButton:disabled{{color:#9ba6b4;background:#eef1f4;}} QPushButton#primary{{background:{NAVY};color:white;font-weight:700;padding:10px 18px;}} QTabWidget::pane{{border:1px solid #b5bec9;background:white;top:-1px;}} QTabBar::tab{{background:#f0f3f7;color:#58708e;padding:10px 16px;border:1px solid #bfc8d2;border-bottom:none;font-size:13px;}} QTabBar::tab:selected{{background:{NAVY};color:white;font-weight:700;}} QLineEdit{{border:1px solid #aeb8c5;padding:6px;}} QPlainTextEdit{{border:1px solid #b8c2ce;}}''')
    @staticmethod
    def title(layout,text,sub=None):
        x=QLabel(text); x.setStyleSheet(f'font-family:Georgia;font-size:23px;font-weight:700;color:{TEXT};'); layout.addWidget(x)
        if sub:
            y=QLabel(sub); y.setStyleSheet(f'font-size:12px;color:{MUTED};'); layout.addWidget(y)
    @staticmethod
    def section(layout,text):
        x=QLabel(text); x.setStyleSheet(f'font-family:Georgia;font-size:17px;font-weight:700;color:{TEXT};padding-top:4px;'); layout.addWidget(x); return x
    @staticmethod
    def banner(layout,text,kind='success'):
        bg,fg=(SUCCESS_BG,SUCCESS) if kind=='success' else (BLUE_BG,'#365a83') if kind=='info' else (WARNING_BG,WARNING) if kind=='warning' else (DANGER_BG,DANGER)
        x=QLabel(text); x.setWordWrap(True); x.setStyleSheet(f'background:{bg};color:{fg};padding:9px 14px;font-weight:600;'); layout.addWidget(x); return x
    @staticmethod
    def note(layout,text,kind='info'):
        return WidgetFactory.banner(layout,text,kind)

def make_table(headers,rows,stretch=True):
    t=QTableWidget(len(rows),len(headers)); t.setHorizontalHeaderLabels(headers); apply_table(t)
    for r,row in enumerate(rows):
        for c,val in enumerate(row): t.setItem(r,c,__import__('PyQt6.QtWidgets',fromlist=['QTableWidgetItem']).QTableWidgetItem(str(val)))
    h=t.horizontalHeader(); h.setSectionResizeMode(QHeaderView.ResizeMode.Stretch if stretch else QHeaderView.ResizeMode.ResizeToContents); t.resizeRowsToContents(); return t
