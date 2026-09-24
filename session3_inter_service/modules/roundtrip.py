from PyQt6.QtWidgets import QHBoxLayout,QLabel
from .base import BaseModule
from .widgets import make_table
from benchmark import roundtrips,streaming
class RoundtripModule(BaseModule):
 def build(self,w):
  self.w=w; lay=self.shell(w); top=QHBoxLayout(); self.widgets.title(top,'Chattiness, and when the first row arrives'); top.addStretch(); self.rb=self.button('Round trips',self.refresh_round,True); self.sb=self.button('Streaming',self.refresh_stream); top.addWidget(self.rb); top.addWidget(self.sb); lay.addLayout(top)
  self.widgets.section(lay,'One batched call against N single calls'); self.table1=make_table(['Codec','Rows','Batched (1 call)','N single calls','Speedup','Round trips saved'],roundtrips()); lay.addWidget(self.table1,1)
  self.stream_title=self.widgets.section(lay,'Unary against server streaming — time to the first usable row'); self.table2=make_table(['Codec','Rows','Unary total ms','Stream total ms','First message ms','Earlier by'],streaming()); lay.addWidget(self.table2,1)
  self.stream_banner=self.widgets.banner(lay,'','success'); self.stream_note=self.widgets.note(lay,'The unary caller waits for the full result set. The streaming caller receives row one while the server continues producing rows. Measurements use the same PostgreSQL transaction rows.','info'); self.update_stream_banner()
 def refresh_round(self):
  self._set_active(self.rb,self.sb); self.table1.setParent(None); self.table1=make_table(['Codec','Rows','Batched (1 call)','N single calls','Speedup','Round trips saved'],roundtrips()); self.w.layout().insertWidget(2,self.table1); self.update_stream_banner()
 def refresh_stream(self):
  self._set_active(self.sb,self.rb); self.table2.setParent(None); self.table2=make_table(['Codec','Rows','Unary total ms','Stream total ms','First message ms','Earlier by'],streaming()); self.w.layout().insertWidget(4,self.table2); self.update_stream_banner()
 def _set_active(self,a,b):
  a.setObjectName('primary'); b.setObjectName(''); a.style().unpolish(a); a.style().polish(a); b.style().unpolish(b); b.style().polish(b)
 def update_stream_banner(self):
  data=streaming(); best=max(data,key=lambda x:float(str(x[5]).replace('x',''))); self.stream_banner.setText(f"Over {best[0]}, the first row arrives after {best[4]} ms streaming against {best[2]} ms unary — {best[5]} earlier, for the same {best[1]:,} rows.")
