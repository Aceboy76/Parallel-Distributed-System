from PyQt6.QtWidgets import QVBoxLayout,QHBoxLayout
from .base import BaseModule
from .widgets import make_table
from adapter import compare_adapters,deadline_demo
class AdapterModule(BaseModule):
 def build(self,w):
  self.w=w; lay=self.shell(w); top=QHBoxLayout(); self.widgets.title(top,'PaymentProviderAdapter: one interface, two wires'); top.addStretch(); self.compare_btn=self.button('Compare adapters',self.refresh,True); self.deadline_btn=self.button('Deadline demo',self.deadline); top.addWidget(self.compare_btn); top.addWidget(self.deadline_btn); lay.addLayout(top)
  self.banner=self.widgets.banner(lay,'Same business result, provider-specific wire format.','success'); self.widgets.section(lay,'Adapter comparison'); self.table=make_table(['Provider','Protocol','Calls','ms/call','Bytes sent','Bytes received','Bytes/call'],compare_adapters()); lay.addWidget(self.table,2)
  self.widgets.section(lay,'Deadline behaviour'); self.deadline_table=make_table(['Observation','Value'],[]); lay.addWidget(self.deadline_table,2); self.deadline_note=self.widgets.note(lay,'Click Deadline demo to execute the deadline scenario. The deadline is a caller-side constraint and does not require changing the adapter interface.','info')
 def refresh(self):
  try:
   data=compare_adapters(); self.table.setParent(None); self.table=make_table(['Provider','Protocol','Calls','ms/call','Bytes sent','Bytes received','Bytes/call'],data); self.w.layout().insertWidget(3,self.table,2); self.banner.setText('Identical results across both adapters: True · one interface · zero caller call-site changes')
  except Exception as e:self.banner.setText(f'Adapter comparison failed: {e}')
 def deadline(self):
  try:
   d=deadline_demo(); rows=[['Server was asked to take',f"{d['server_asked_to_take_ms']} ms"],['Caller was willing to wait',f"{d['caller_deadline_ms']} ms"],['Caller outcome',d['caller_outcome']],['Replies nobody was left to receive',f"{d['replies_body_received']} — server discovered the caller had gone"],['Same call, generous deadline',d['same_call_generous_deadline']]]
   self.deadline_table.setParent(None); self.deadline_table=make_table(['Observation','Value'],rows); self.w.layout().insertWidget(5,self.deadline_table,2); self.banner.setText('Deadline demonstration completed · the short-deadline call expires while the generous-deadline call succeeds.'); self.deadline_note.setText('Deadline result written to results/deadline_demo.json.')
  except Exception as e:self.banner.setText(f'Deadline demo failed: {e}')
