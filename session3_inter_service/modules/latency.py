from PyQt6.QtWidgets import QVBoxLayout,QHBoxLayout
from .base import BaseModule
from .widgets import make_table,BarChart
from benchmark import latency
class LatencyModule(BaseModule):
 def build(self,w):
  self.w=w; lay=self.shell(w); top=QHBoxLayout(); self.widgets.title(top,'One RPC, three transports'); top.addStretch(); top.addWidget(self.button('Benchmark',self.refresh,True)); lay.addLayout(top); self.banner=self.widgets.banner(lay,'In-process is the no-wire baseline; HTTP rows include actual local transport and codec work.','info'); self.chart=BarChart(); lay.addWidget(self.chart,2); self.table=None; self.refresh()
 def refresh(self):
  try:
   data=latency(); self.banner.setText(' · '.join(f'{r[0]} {r[3]} ms at {r[5]} bytes/call' for r in data));
   if self.table:self.table.setParent(None)
   self.table=make_table(['Transport','Codec','Calls','Median ms','Calls/sec','Bytes/call'],data); self.w.layout().addWidget(self.table,2); self.chart.set_data([(r[0],r[3]) for r in data],'ms/call')
  except Exception as e:self.banner.setText(f'Database/benchmark unavailable: {e}')
