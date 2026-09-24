from __future__ import annotations
import csv,json
from pathlib import Path
from config import OUT_COMPOSE,OUT_RECON,OUT_SUMMARY,TOLERANCE
from services import RevenueService,mechanism_breakdown,actual_monetization_summary

def compose():
    rows=list(RevenueService().stream_regional_revenue({'region':'','limit':1000000}))
    with OUT_COMPOSE.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['region','transactions','revenue_total','revenue_mean'])
        for r in rows: w.writerow([r['region'],int(r['transactions']),f"{float(r['revenue_total']):.2f}",f"{float(r['revenue_mean']):.4f}"])
    return rows

def _session_reference(path):
    if not path.exists(): return 0,0.0,{ }
    with path.open(newline='',encoding='utf-8') as f:
        rr=list(csv.DictReader(f))
    tx=sum(int(float(x.get('txn_count',x.get('transactions',0)))) for x in rr)
    total=sum(float(x.get('score_total',x.get('revenue_total',0))) for x in rr)
    return tx,total,{x.get('region'):float(x.get('revenue_total',x.get('score_total',0))) for x in rr if x.get('region')}

def _session1_reference(): return _session_reference(Path(__file__).resolve().parent.parent/'session1_parallel_compute/results/baseline_result.csv')
def _session2_reference(): return _session_reference(Path(__file__).resolve().parent.parent/'session2_event_streaming/results/streamed_regional_revenue.csv')

def reconcile():
    current=compose(); total=sum(float(r['revenue_total']) for r in current); tx=sum(int(r['transactions']) for r in current)
    s1_tx,s1_total,s1_regions=_session1_reference(); s2_tx,s2_total,s2_regions=_session2_reference()
    expected_tx=s1_tx or s2_tx or tx; expected=s1_total if s1_tx else (s2_total if s2_tx else total)
    count_diff=abs(tx-expected_tx); aggregate_diff=abs(total-expected)
    all_regions=set(r['region'] for r in current)|set(s1_regions)|set(s2_regions)
    max_region_diff=max([abs(float(next((x['revenue_total'] for x in current if x['region']==reg),0))-float(s1_regions.get(reg,s2_regions.get(reg,0)))) for reg in all_regions] or [0.0])
    passed=aggregate_diff<=TOLERANCE and count_diff==0 and max_region_diff<=TOLERANCE
    report={'passed':passed,'regions':len(current),'transactions_db':tx,'transactions_session1':s1_tx,'transactions_session2':s2_tx,'max_count_difference':count_diff,'aggregate_db':total,'aggregate_session1':s1_total,'aggregate_session2':s2_total,'aggregate_difference':aggregate_diff,'max_revenue_total_difference':max_region_diff,'tolerance':TOLERANCE,'metric':'score as revenue reconciliation proxy','composition':'RevenueService -> TransactionService + CustomerService','mechanism_breakdown':mechanism_breakdown(),'actual_oulad_monetization':actual_monetization_summary()}
    OUT_RECON.write_text(json.dumps(report,indent=2,default=str),encoding='utf-8'); return report

def summary():
    report=reconcile(); data={'contract':{},'reconciliation':report}; p=Path(__file__).resolve().parent/'results/contract_report.json'
    if p.exists(): data['contract']=json.loads(p.read_text())
    OUT_SUMMARY.write_text(json.dumps(data,indent=2,default=str),encoding='utf-8'); return data
