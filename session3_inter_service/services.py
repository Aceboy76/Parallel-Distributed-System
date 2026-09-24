from __future__ import annotations
import time
from collections import defaultdict
from config import PASS_SCORE, UPSELL_SCORE
def fetchall(*args, **kwargs):
    from db import fetchall as _fetchall
    return _fetchall(*args, **kwargs)

def fetchone(*args, **kwargs):
    from db import fetchone as _fetchone
    return _fetchone(*args, **kwargs)

class ServiceFailure(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message); self.code=code; self.message=message; self.details=details or {}

class CustomerService:
    def get_customer(self, req, **_):
        row=customer(int(req.get('customer_id',0)))
        if not row: raise ServiceFailure('NOT_FOUND','Customer not found',{'customer_id':req.get('customer_id')})
        return row
    def batch_get_customers(self, req, **_):
        ids=[int(x) for x in req.get('customer_ids',[])]
        rows=customers(ids)
        found={int(r['id_student']) for r in rows}; missing=[x for x in ids if x not in found]
        if missing: raise ServiceFailure('NOT_FOUND','One or more customers not found',{'missing_ids':missing})
        return {'customers':rows}

class ConfigService:
    def get_config(self, req, **_):
        cid=req.get('config_id','oulad-score-proxy')
        if cid!='oulad-score-proxy': raise ServiceFailure('NOT_FOUND','Config not found',{'config_id':cid})
        return {'config_id':cid,'name':'OULAD score proxy','pass_score':PASS_SCORE,'upsell_score':UPSELL_SCORE,'proxy_metric':'score','note':'Score is a reconciliation proxy; OULAD has no native transaction revenue field.'}
    def list_configs(self, req, **_): return {'configs':['oulad-score-proxy']}

class EntitlementService:
    def get_entitlement(self, req, **_):
        row=entitlement(int(req.get('customer_id',0)))
        if not row: raise ServiceFailure('NOT_FOUND','Entitlement not found',{'customer_id':req.get('customer_id')})
        return row

class TransactionService:
    def count_transactions(self, req, **_): return {'value':count_transactions()}
    def list_transactions(self, req, **_):
        rows=transactions(customer_id=req.get('customer_id'),region=req.get('region'),limit=int(req.get('limit') or 50))
        return {'transactions':rows}
    def stream_transactions(self, req, deadline=None, started=None, **_):
        rows=transactions(customer_id=req.get('customer_id'),region=req.get('region'),limit=int(req.get('limit') or 5000))
        for row in rows:
            if deadline is not None and started is not None and time.perf_counter()-started > deadline: raise ServiceFailure('DEADLINE_EXCEEDED','Caller deadline exceeded')
            yield row

class RevenueService:
    def __init__(self): self.customer_service=CustomerService(); self.transaction_service=TransactionService()
    def _compose_rows(self, req):
        rows=self.transaction_service.list_transactions({'region':req.get('region'),'limit':int(req.get('limit') or 1000000)})['transactions']
        ids=sorted({int(r['id_student']) for r in rows})
        customers_result=self.customer_service.batch_get_customers({'customer_ids':ids})['customers'] if ids else []
        region_by_id={int(r['id_student']):r['region'] for r in customers_result}
        grouped=defaultdict(list)
        for r in rows:
            region=region_by_id.get(int(r['id_student']),r.get('region') or '')
            grouped[region].append(float(r.get('score') or 0))
        return grouped
    def compute_regional_revenue(self, req, **kwargs):
        grouped=self._compose_rows(req)
        return {'regions':sorted(grouped),'transaction_total':sum(len(v) for v in grouped.values()),'revenue_total':sum(sum(v) for v in grouped.values())}
    def stream_regional_revenue(self, req, **kwargs):
        grouped=self._compose_rows(req)
        for region in sorted(grouped):
            vals=grouped[region]
            yield {'region':region,'transactions':len(vals),'revenue_total':sum(vals),'revenue_mean':sum(vals)/len(vals) if vals else 0.0}

class ChargeService:
    def charge(self, req, deadline=None, started=None, **_):
        delay=max(0,int(req.get('delay_ms') or 0))/1000
        if delay: time.sleep(delay)
        if deadline is not None and delay > deadline: raise ServiceFailure('DEADLINE_EXCEEDED','Caller deadline exceeded during charge')
        return {'charge_id':'charge-'+str(req.get('idempotency_key','demo')),'status':'succeeded','amount_cents':int(req.get('amount_cents') or 0),'provider':'score-proxy'}

def transaction_sample(limit=1):
    return fetchall('''SELECT sa.id_assessment, sa.id_student, ad.assessment_type, c.region, sa.score, sa.date_submitted
                       FROM student_assessment sa JOIN customers c ON c.id_student=sa.id_student
                       LEFT JOIN assessment_defs ad ON ad.id_assessment=sa.id_assessment
                       ORDER BY sa.date_submitted, sa.id_student, sa.id_assessment LIMIT %s''',(limit,))

def customer(customer_id): return fetchone('SELECT id_student, gender, region, highest_education, disability FROM customers WHERE id_student=%s',(customer_id,))
def customers(ids): return fetchall('SELECT id_student, gender, region, highest_education, disability FROM customers WHERE id_student = ANY(%s)',(ids,)) if ids else []
def entitlement(customer_id): return fetchone('SELECT id_student, date_registration, date_unregistration FROM entitlements WHERE id_student=%s',(customer_id,))
def count_transactions(): return int(fetchone('SELECT COUNT(*) AS n FROM student_assessment')['n'])
def transactions(customer_id=None, region=None, limit=50):
    clauses=[]; params=[]
    if customer_id is not None: clauses.append('sa.id_student=%s'); params.append(customer_id)
    if region: clauses.append('c.region=%s'); params.append(region)
    where=(' WHERE '+ ' AND '.join(clauses)) if clauses else ''
    params.append(int(limit))
    return fetchall(f'''SELECT sa.id_assessment, sa.id_student, ad.assessment_type, c.region, sa.score, sa.date_submitted
                        FROM student_assessment sa JOIN customers c ON c.id_student=sa.id_student
                        LEFT JOIN assessment_defs ad ON ad.id_assessment=sa.id_assessment
                        {where} ORDER BY sa.date_submitted, sa.id_student, sa.id_assessment LIMIT %s''',params)
def regional_revenue(region=None, limit=None):
    params=[]; where=''
    if region: where=' WHERE c.region=%s'; params.append(region)
    sql='''SELECT c.region, COUNT(sa.score)::bigint AS transactions, COALESCE(SUM(sa.score),0)::double precision AS revenue_total, COALESCE(AVG(sa.score),0)::double precision AS revenue_mean FROM student_assessment sa JOIN customers c ON c.id_student=sa.id_student %s GROUP BY c.region ORDER BY c.region''' % where
    rows=fetchall(sql,params); return rows[:int(limit)] if limit else rows

def mechanism(score, date_submitted, date_unregistration):
    if date_unregistration is not None and int(date_submitted) >= int(date_unregistration): return 'Revenue at risk / lost'
    if score is None: return 'Early intervention / outcome pending'
    score=float(score)
    if score < PASS_SCORE: return 'Resit / repeat revenue'
    if score >= UPSELL_SCORE: return 'Revenue secured + upsell next module'
    return 'Revenue secured / continuation revenue'
def mechanism_breakdown():
    rows=fetchall('SELECT sa.score, sa.date_submitted, e.date_unregistration FROM student_assessment sa JOIN entitlements e ON e.id_student=sa.id_student')
    out=defaultdict(lambda:[0,0.0])
    for r in rows: k=mechanism(r['score'],r['date_submitted'],r['date_unregistration']); out[k][0]+=1; out[k][1]+=float(r['score'] or 0)
    return [{'mechanism':k,'events':v[0],'revenue_proxy':v[1]} for k,v in sorted(out.items())]
def regional_from_db(): return regional_revenue()
def streaming_rows(limit=5000): return transactions(limit=limit)
def actual_monetization_summary(): return fetchone('SELECT COUNT(*)::bigint AS events, COALESCE(SUM(total_revenue),0)::double precision AS revenue_total FROM oulad_monetization')

if __name__=='__main__':
    print('Service registry definitions: CustomerService, ConfigService, EntitlementService, TransactionService, RevenueService, ChargeService')
    print('RevenueService composition: TransactionService -> CustomerService -> regional aggregation')
    print('Typed failures: NOT_FOUND, DEADLINE_EXCEEDED, INTERNAL')
