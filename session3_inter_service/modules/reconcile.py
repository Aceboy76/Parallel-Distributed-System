from PyQt6.QtWidgets import QVBoxLayout,QHBoxLayout
from .base import BaseModule
from .widgets import make_table
from compose import reconcile,compose
class ReconcileModule(BaseModule):
 def build(self,w):
  self.w=w; lay=self.shell(w); top=QHBoxLayout(); self.widgets.title(top,'Three execution models, one number'); top.addStretch(); top.addWidget(self.button('Compose only',self.compose)); top.addWidget(self.button('Reconcile now',self.refresh,True)); lay.addLayout(top); self.banner=self.widgets.banner(lay,'Click Reconcile now to query PostgreSQL and compare with Session 1.','info'); self.table=None; self.reg_table=None; self.refresh()
 def refresh(self):
  try:
   r=reconcile(); self.banner.setText(f"{'PASSED' if r['passed'] else 'FAILED'} — {r['regions']} regions, {r['transactions_db']:,} scored transactions, {r['aggregate_db']:,.2f} score/revenue proxy. Session 1 agreement: {r['passed']}")
   rows=[['protobuf vs JSON',r['regions'],r['transactions_db'],r['max_count_difference'],f"{r['aggregate_difference']:.3e}",'PASSED' if r['passed'] else 'FAILED'],['Session 1 (Spark batch)',r['regions'],r['transactions_session1'],r['max_count_difference'],f"{r['aggregate_difference']:.3e}",'PASSED' if r['passed'] else 'FAILED'],['Session 2 (event stream)',r['regions'],r['transactions_session2'],r['max_count_difference'],f"{r['aggregate_difference']:.3e}",'PASSED' if r['passed'] else 'FAILED']]
   if self.table:self.table.setParent(None)
   self.table=make_table(['Compared against','Regions','Transactions','Max count diff','Max mean/aggregate diff','Verdict'],rows); self.w.layout().addWidget(self.table,1)
   self.widgets.section(self.w.layout(),'Composed regional revenue (results/service_regional_revenue.csv)')
   reg=compose();
   if self.reg_table:self.reg_table.setParent(None)
   self.reg_table=make_table(['Region','Transactions','Revenue total','Revenue mean'],[[x['region'],x['transactions'],f"{float(x['revenue_total']):,.2f}",f"{float(x['revenue_mean']):.4f}"] for x in reg]); self.w.layout().addWidget(self.reg_table,3)
  except Exception as e:self.banner.setText(f'Database/reconciliation unavailable: {e}')
 def compose(self):
  try:
   rows=compose(); self.banner.setText(f'Composed {len(rows)} regional rows from PostgreSQL → results/service_regional_revenue.csv'); self.refresh()
  except Exception as e:self.banner.setText(f'Compose failed: {e}')
