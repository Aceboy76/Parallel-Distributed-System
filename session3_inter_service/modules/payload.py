from PyQt6.QtWidgets import QVBoxLayout,QHBoxLayout,QLabel
from .base import BaseModule
from .widgets import make_table,BarChart
from benchmark import payload
class PayloadModule(BaseModule):
 def build(self,w):
  self.w=w; lay=self.shell(w); top=QHBoxLayout(); self.widgets.title(top,'The same message, two formats'); top.addStretch(); top.addWidget(self.button('Measure',self.refresh,True)); lay.addLayout(top); self.banner=self.widgets.banner(lay,'Run Measure to compare actual PostgreSQL-backed sample messages.','info'); self.chart=BarChart(); lay.addWidget(self.chart,2); self.table=None
  self.refresh()
 def refresh(self):
  try:
   data=payload();
   if self.table:self.table.setParent(None)
   self.table=make_table(['Message','Fields','JSON bytes','protobuf bytes','Saved','Reduction'],data); self.w.layout().addWidget(self.table,2)
   self.chart.set_data([(r[0],r[2]) for r in data],'bytes'); best=max(data,key=lambda x:float(x[5])); tx=next((x for x in data if x[0]=='Transaction'),best); self.banner.setText(f"Transaction: {tx[2]} bytes as JSON, {tx[3]} as protobuf — {tx[5]}% smaller. Best case here is {best[0]} at {best[5]}%. Sample values are generated from the first ordered PostgreSQL assessment record.")
  except Exception as e:self.banner.setText(f'Database/measurement unavailable: {e}')
