from __future__ import annotations
import sys,threading,traceback
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFrame,QLabel,QPushButton,QTabWidget
from modules.widgets import WidgetFactory,NAVY,NAVY_2,SUCCESS,SUCCESS_BG,DANGER,DANGER_BG,WARNING,WARNING_BG
from modules.pipeline import PipelineModule
from modules.contract import ContractModule
from modules.payload import PayloadModule
from modules.latency import LatencyModule
from modules.roundtrip import RoundtripModule
from modules.adapter import AdapterModule
from modules.reconcile import ReconcileModule
from modules.console import ConsoleModule
from pipeline import run_all
APP_TITLE='CMA-Flow — Session 3 Inter-Service Communication Console'
class CMAFlowApp(QMainWindow):
 def __init__(self):
  super().__init__(); self.setWindowTitle(APP_TITLE); self.resize(1500,930); self.setMinimumSize(1180,760); self.widgets=WidgetFactory(self); self.widgets.setup_style(); self.events=[]; self.running=False; self.build_header(); self.build_tabs(); self.build_footer(); self.timer=QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(100)
 def build_header(self):
  h=QFrame(); h.setFixedHeight(112); h.setStyleSheet(f'background:{NAVY};'); l=QHBoxLayout(h); l.setContentsMargins(26,16,24,14); left=QVBoxLayout(); t=QLabel('CMA-Flow — Session 3 Inter-Service Communication'); t.setStyleSheet('color:white;font-family:Georgia;font-size:25px;font-weight:700;'); left.addWidget(t); s=QLabel('MIT 261 Parallel and Distributed Systems  ·  typed contract · two codecs · three transports · PostgreSQL-backed OULAD'); s.setStyleSheet('color:#c7d7ee;font-size:12px;'); left.addWidget(s); l.addLayout(left,1); self.status=QLabel('●  READY'); self.status.setStyleSheet('background:#edf2f7;color:#4a6078;padding:9px 12px;font-weight:700;'); l.addWidget(self.status); b=QPushButton('Refresh'); b.clicked.connect(self.refresh_all); l.addWidget(b); self.run_all_btn=QPushButton('▶  Run everything'); self.run_all_btn.setObjectName('primary'); self.run_all_btn.clicked.connect(self.run_everything); l.addWidget(self.run_all_btn); self.setMenuWidget(h)
 def build_tabs(self):
  shell=QWidget(); lay=QVBoxLayout(shell); lay.setContentsMargins(12,10,12,5); self.tabs=QTabWidget(); lay.addWidget(self.tabs); self.pipeline=PipelineModule(self); self.contract=ContractModule(self); self.payload=PayloadModule(self); self.latency=LatencyModule(self); self.roundtrip=RoundtripModule(self); self.adapter=AdapterModule(self); self.reconcile=ReconcileModule(self); self.console_module=ConsoleModule(self)
  for title,module in [('Pipeline',self.pipeline),('Contract',self.contract),('Payload size',self.payload),('Latency',self.latency),('Round trips & streaming',self.roundtrip),('Adapter swap',self.adapter),('Reconciliation',self.reconcile),('Console',self.console_module)]:
   w=QWidget(); self.tabs.addTab(w,title); module.build(w)
  self.setCentralWidget(shell)
 def build_footer(self):
  f=QFrame(); f.setFixedHeight(30); f.setStyleSheet(f'background:{NAVY_2};'); l=QHBoxLayout(f); l.setContentsMargins(14,0,14,0); self.footer=QLabel('CMA-Flow ready'); self.footer.setStyleSheet('color:#d7e4f5;font-size:11px;'); l.addWidget(self.footer); l.addStretch(); x=QLabel('Session 3  ·  Python / PostgreSQL / JSON + protobuf'); x.setStyleSheet('color:#8fa7c5;font-size:11px;'); l.addWidget(x); self.centralWidget().layout().addWidget(f)
 def set_status(self,text,kind='ready'):
  st={'ready':('#edf2f7','#4a6078'),'running':(WARNING_BG,WARNING),'passed':(SUCCESS_BG,SUCCESS),'failed':(DANGER_BG,DANGER)}; bg,fg=st.get(kind,st['ready']); self.status.setText('●  '+text); self.status.setStyleSheet(f'background:{bg};color:{fg};padding:9px 12px;font-weight:700;')
 def refresh_all(self):
  for m in [self.contract,self.payload,self.latency,self.roundtrip,self.adapter,self.reconcile]:
   try:
    if hasattr(m,'refresh'):m.refresh()
   except Exception as e:self.console_module.write(str(e))
  self.footer.setText('Results refreshed · ready')
 def update_stage(self,name,status,headline): self.pipeline.update(name,status,headline); self.console_module.write(f'{name}: {status} — {headline}')
 def run_everything(self):
  if self.running:return
  self.running=True; self.run_all_btn.setEnabled(False); self.set_status('RUNNING','running'); self.tabs.setCurrentIndex(7)
  def worker():
   try:
    run_all(lambda n,s,h:self.events.append(('stage',n,s,h))); self.events.append(('all_done',))
   except Exception as e:self.events.append(('error',str(e),traceback.format_exc()))
  threading.Thread(target=worker,daemon=True).start()
 def run_stage(self,name):
  mapping={'Contract':__import__('contract').run,'Wire format':__import__('benchmark').wire_check,'Serve':__import__('pipeline').serve_info,'Payload size':__import__('benchmark').payload,'Unary latency':__import__('benchmark').latency,'Round trips':__import__('benchmark').roundtrips,'Streaming':__import__('benchmark').streaming,'Adapter swap':__import__('adapter').compare_adapters,'Deadline':__import__('adapter').deadline_demo,'Compose':__import__('compose').compose,'Reconcile':__import__('compose').reconcile}
  if name not in mapping:return
  try:self.update_stage(name,'running',''); r=mapping[name](); self.update_stage(name,'passed',self._stage_headline(name,r)); self.refresh_all()
  except Exception as e:self.update_stage(name,'failed',str(e))

 def _stage_headline(self,name,r):
  if name=='Contract': return f"{r['messages']} messages, {r['methods']} methods, {r['services']} services, {r['streaming_methods']} streaming"
  if name=='Serve': return f"{r['services']} services on {r['host']} · {r['transactions']:,} DB assessment rows"
  if name=='Wire format': return f"{r['message']} · JSON {r['json_bytes']} B → protobuf {r['protobuf_bytes']} B"
  if name=='Payload size': return f"{len(r)} DB-backed message samples measured"
  if name=='Unary latency': return f"{r[0][3]} ms in-process · {r[1][3]} ms JSON · {r[2][3]} ms protobuf"
  if name=='Round trips': return f"{r[0][4]} JSON speedup · {r[0][5]} round trips saved"
  if name=='Streaming': return f"{r[0][5]} earlier first row over {r[0][1]:,} rows"
  if name=='Adapter swap': return f"{r[0][0]} {r[0][3]} ms/call · {r[1][0]} {r[1][3]} ms/call"
  if name=='Deadline': return r['caller_outcome']
  if name=='Compose': return f"{len(r)} regional rows composed from PostgreSQL"
  if name=='Reconcile': return f"{r['regions']} regions · {r['transactions_db']:,} scored transactions · {r['aggregate_db']:,.2f} · {'PASSED' if r['passed'] else 'FAILED'}"
  return 'completed'

 def poll(self):
  while self.events:
   e=self.events.pop(0)
   if e[0]=='stage':self.update_stage(e[1],e[2],e[3])
   elif e[0]=='all_done':self.running=False; self.run_all_btn.setEnabled(True); self.set_status('PASSED','passed'); self.footer.setText('All stages completed successfully'); self.refresh_all()
   elif e[0]=='error':self.running=False; self.run_all_btn.setEnabled(True); self.set_status('FAILED','failed'); self.console_module.write(e[2]); self.footer.setText('Pipeline failed')
 def closeEvent(self,e):e.accept()
if __name__=='__main__': app=QApplication(sys.argv); w=CMAFlowApp(); w.show(); sys.exit(app.exec())
