from pathlib import Path
from PyQt6.QtWidgets import QVBoxLayout,QHBoxLayout,QTableWidget,QTableWidgetItem,QHeaderView
from .base import BaseModule
from .widgets import SUCCESS_BG,apply_table,make_table
from config import ARTIFACTS, RESULTS_DIR
class PipelineModule(BaseModule):
    stages=['Contract','Wire format','Serve','Payload size','Unary latency','Round trips','Streaming','Adapter swap','Deadline','Compose','Reconcile']
    def build(self,w):
        self.w=w; lay=self.shell(w); top=QHBoxLayout(); self.widgets.title(top,'Pipeline','Session 3 evidence chain · every business result is PostgreSQL-backed OULAD data'); top.addStretch(); self.run_btn=self.button('Run everything',self.run_all,True); top.addWidget(self.run_btn); self.refresh_btn=self.button('Refresh artifacts',self.refresh); top.addWidget(self.refresh_btn); lay.addLayout(top)
        cards=QHBoxLayout(); self.db_card=self.widgets.card(cards,'—','assessment rows in PostgreSQL'); self.region_card=self.widgets.card(cards,'—','regions in the database'); self.art_card=self.widgets.card(cards,'—','artifacts in results/'); self.status_card=self.widgets.card(cards,'READY','pipeline status'); lay.addLayout(cards)
        bar=QHBoxLayout()
        for s in self.stages: bar.addWidget(self.button(s,self.make_stage(s)))
        lay.addLayout(bar)
        self.table=QTableWidget(len(self.stages),3); self.table.setHorizontalHeaderLabels(['Stage','Status','Headline result']); apply_table(self.table); self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents); self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents); self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch); lay.addWidget(self.table,2); self.reset()
        self.widgets.section(lay,'Artefacts in results/')
        self.art_table=QTableWidget(0,4); self.art_table.setHorizontalHeaderLabels(['Artefact','Written by','Status','Size']); apply_table(self.art_table); self.art_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); lay.addWidget(self.art_table,2); self.refresh()
    def reset(self):
        for i,s in enumerate(self.stages):
            self.table.setItem(i,0,QTableWidgetItem(f'{i+1}. {s}')); self.table.setItem(i,1,QTableWidgetItem('not run')); self.table.setItem(i,2,QTableWidgetItem(''))
    def make_stage(self,name): return lambda:self.app.run_stage(name)
    def run_all(self): self.app.run_everything()
    def update(self,name,status,headline):
        if name not in self.stages:return
        r=self.stages.index(name); self.table.setItem(r,1,QTableWidgetItem(status)); self.table.setItem(r,2,QTableWidgetItem(headline))
        for c in range(3):
            it=self.table.item(r,c)
            if it and status=='passed': it.setBackground(__import__('PyQt6.QtGui',fromlist=['QBrush']).QBrush(__import__('PyQt6.QtGui',fromlist=['QColor']).QColor(SUCCESS_BG)))
        self.status_card.setText('PASSED' if status=='passed' else status.upper()); self.refresh()
    def refresh(self):
        try:
            from db import fetchone,fetchall
            n=int(fetchone('SELECT COUNT(*) AS n FROM student_assessment')['n']); regions=int(fetchone('SELECT COUNT(DISTINCT region) AS n FROM customers')['n']); self.db_card.setText(f'{n:,}'); self.region_card.setText(str(regions))
        except Exception as e:
            self.db_card.setText('DB error'); self.region_card.setText('—')
        rows=[]
        writers={'contract_report.json':'contracts.py','payload_sizes.csv':'benchmark.py — payload','latency_benchmark.csv':'benchmark.py — latency','roundtrip_benchmark.csv':'benchmark.py — round trips','streaming_benchmark.csv':'benchmark.py — streaming','adapter_comparison.csv':'adapter.py','deadline_demo.json':'adapter.py','service_regional_revenue.csv':'compose.py','reconciliation_report.json':'compose.py','session3_summary.json':'compose.py','event_schema.json':'pipeline.py'}
        for p in ARTIFACTS:
            status='written' if p.exists() else 'not yet'; size=f'{p.stat().st_size:,} B' if p.exists() else '—'; rows.append([p.name,writers.get(p.name,'Session 3'),status,size])
        self.art_table.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,v in enumerate(row): self.art_table.setItem(r,c,QTableWidgetItem(str(v)))
        self.art_card.setText(str(sum(1 for p in ARTIFACTS if p.exists())))
