from PyQt6.QtWidgets import QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QPlainTextEdit,QSplitter
from PyQt6.QtCore import Qt
from .base import BaseModule
from contracts import MESSAGES,SERVICES,field_count,method_count
from contract import render_proto
from .widgets import apply_table
from pathlib import Path
class ContractModule(BaseModule):
 def build(self,w):
  self.w=w; lay=self.shell(w); top=QHBoxLayout(); self.widgets.title(top,'One schema, written once'); top.addStretch(); top.addWidget(self.button('Check the encoder',self.check_encoder)); top.addWidget(self.button('Verify against cma.proto',self.verify,True)); lay.addLayout(top)
  self.banner=self.widgets.banner(lay,'Loading contract…','info')
  split=QSplitter(Qt.Orientation.Horizontal); left=__import__('PyQt6.QtWidgets',fromlist=['QWidget']).QWidget(); ll=QVBoxLayout(left); ll.setContentsMargins(0,0,8,0)
  ll.addWidget(QLabel('Methods')); self.table=QTableWidget(method_count(),5); self.table.setHorizontalHeaderLabels(['Service','Method','Request','Response','Kind']); apply_table(self.table); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
  r=0
  for s,ms in SERVICES.items():
   for m,req,res,k in ms:
    for c,v in enumerate([s,m,req,res,k]): self.table.setItem(r,c,QTableWidgetItem(v))
    r+=1
  ll.addWidget(self.table,1); ll.addWidget(QLabel('Message fields')); f=QTableWidget(field_count(),5); f.setHorizontalHeaderLabels(['Message','#','Field','Type','Wire type']); apply_table(f); f.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); rr=0; wire={'int32':'varint','int64':'varint','bool':'varint','double':'fixed64','string':'length-delimited'}
  for m in MESSAGES:
   for fld in m.fields:
    for c,v in enumerate([m.name,fld.number,fld.name,('repeated '+fld.typ if fld.repeated else fld.typ),wire[fld.typ]]): f.setItem(rr,c,QTableWidgetItem(str(v)))
    rr+=1
  ll.addWidget(f,2); split.addWidget(left)
  right=__import__('PyQt6.QtWidgets',fromlist=['QWidget']).QWidget(); rl=QVBoxLayout(right); rl.setContentsMargins(8,0,0,0); rl.addWidget(QLabel('cma.proto')); self.proto=QPlainTextEdit(); self.proto.setReadOnly(True); self.proto.setStyleSheet('background:#102a4d;color:#e6edf6;font-family:Consolas;font-size:12px;padding:8px;'); self.proto.setPlainText(self.current_proto()); rl.addWidget(self.proto,1); split.addWidget(right); split.setSizes([1000,450]); lay.addWidget(split,1); self.update_banner()
 def current_proto(self):
  p=Path(__file__).resolve().parents[1]/'cma.proto'; return p.read_text(encoding='utf-8') if p.exists() else render_proto()
 def update_banner(self):
  p=Path(__file__).resolve().parents[1]/'cma.proto'; sync=p.exists() and p.read_text(encoding='utf-8').strip()==render_proto().strip(); self.banner.setText(f'{len(MESSAGES)} messages, {field_count()} fields, {len(SERVICES)} services, {method_count()} methods (2 server-streaming) · contracts.py in sync with cma.proto: {sync}'); self.proto.setPlainText(self.current_proto())
 def check_encoder(self):
  try:
   from benchmark import wire_check
   r=wire_check(); self.banner.setText(f"Encoder check passed · {r['message']} · JSON {r['json_bytes']} B → protobuf {r['protobuf_bytes']} B · sample read from PostgreSQL")
  except Exception as e:self.banner.setText(f'Encoder check failed: {e}')
 def verify(self):
  from contract import run
  run(); self.update_banner()
