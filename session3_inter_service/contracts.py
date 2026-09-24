from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Field:
    name: str
    number: int
    typ: str
    repeated: bool = False

@dataclass(frozen=True)
class Message:
    name: str
    fields: tuple[Field, ...]

MESSAGES = [
    Message('Empty', ()),
    Message('Count', (Field('value',1,'int64'),)),
    Message('RpcError', (Field('code',1,'string'),Field('message',2,'string'),Field('details',3,'string'))),
    Message('ChargeRequest', (Field('amount_cents',1,'int64'),Field('customer_id',2,'string'),Field('currency',3,'string'),Field('idempotency_key',4,'string'),Field('delay_ms',5,'int32'))),
    Message('ChargeResult', (Field('charge_id',1,'string'),Field('status',2,'string'),Field('amount_cents',3,'int64'),Field('provider',4,'string'))),
    Message('ConfigRequest', (Field('config_id',1,'string'),)),
    Message('MonetizationConfig', (Field('config_id',1,'string'),Field('name',2,'string'),Field('pass_score',3,'double'),Field('upsell_score',4,'double'),Field('proxy_metric',5,'string'),Field('note',6,'string'))),
    Message('ConfigList', (Field('configs',1,'string',True),)),
    Message('CustomerRequest', (Field('customer_id',1,'int64'),)),
    Message('CustomerBatchRequest', (Field('customer_ids',1,'int64',True),)),
    Message('Customer', (Field('id_student',1,'int64'),Field('gender',2,'string'),Field('region',3,'string'),Field('highest_education',4,'string'),Field('disability',5,'string'))),
    Message('CustomerBatch', (Field('customers',1,'string',True),)),
    Message('EntitlementRequest', (Field('customer_id',1,'int64'),)),
    Message('Entitlement', (Field('id_student',1,'int64'),Field('date_registration',2,'double'),Field('date_unregistration',3,'double'))),
    Message('RevenueQuery', (Field('region',1,'string'),Field('limit',2,'int32'))),
    Message('RegionRevenue', (Field('region',1,'string'),Field('transactions',2,'int64'),Field('revenue_total',3,'double'),Field('revenue_mean',4,'double'))),
    Message('RegionalRevenueReport', (Field('regions',1,'string',True),Field('transaction_total',2,'int64'),Field('revenue_total',3,'double'))),
    Message('TransactionQuery', (Field('customer_id',1,'int64'),Field('region',2,'string'),Field('limit',3,'int32'))),
    Message('Transaction', (Field('id_assessment',1,'int64'),Field('id_student',2,'int64'),Field('assessment_type',3,'string'),Field('region',4,'string'),Field('score',5,'double'),Field('timestamp',6,'string'))),
    Message('TransactionList', (Field('transactions',1,'string',True),)),
]

SERVICES = {
    'ChargeService': [('Charge','ChargeRequest','ChargeResult','unary')],
    'ConfigService': [('GetConfig','ConfigRequest','MonetizationConfig','unary'),('ListConfigs','Empty','ConfigList','unary')],
    'CustomerService': [('BatchGetCustomers','CustomerBatchRequest','CustomerBatch','unary'),('GetCustomer','CustomerRequest','Customer','unary')],
    'EntitlementService': [('GetEntitlement','EntitlementRequest','Entitlement','unary')],
    'RevenueService': [('ComputeRegionalRevenue','RevenueQuery','RegionalRevenueReport','unary'),('StreamRegionalRevenue','RevenueQuery','RegionRevenue','server-streaming')],
    'TransactionService': [('CountTransactions','Empty','Count','unary'),('ListTransactions','TransactionQuery','TransactionList','unary'),('StreamTransactions','TransactionQuery','Transaction','server-streaming')],
}

def message_map(): return {m.name:m for m in MESSAGES}
def field_count(): return sum(len(m.fields) for m in MESSAGES)
def method_count(): return sum(len(v) for v in SERVICES.values())

def sample_for(name: str, db_row: dict[str, Any] | None = None):
    r = db_row or {}
    if name == 'Empty': return {}
    if name == 'Count': return {'value': 173739}
    if name == 'RpcError': return {'code':'NOT_FOUND','message':'Customer not found','details':'customer_id=999999999'}
    if name == 'ChargeRequest': return {'amount_cents': int(float(r.get('score') or 0)*100), 'customer_id': str(r.get('id_student',0)), 'currency':'SCORE', 'idempotency_key':'cma-demo-1', 'delay_ms':0}
    if name == 'ChargeResult': return {'charge_id':'charge-demo-1','status':'succeeded','amount_cents':int(float(r.get('score') or 0)*100),'provider':'score-proxy'}
    if name == 'ConfigRequest': return {'config_id':'oulad-score-proxy'}
    if name == 'MonetizationConfig': return {'config_id':'oulad-score-proxy','name':'OULAD score proxy','pass_score':40.0,'upsell_score':80.0,'proxy_metric':'score','note':'Score is a reconciliation proxy; OULAD has no native transaction revenue field.'}
    if name == 'ConfigList': return {'configs':['oulad-score-proxy']}
    if name == 'CustomerRequest': return {'customer_id':int(r.get('id_student',0))}
    if name == 'CustomerBatchRequest': return {'customer_ids':[int(r.get('id_student',0))] * 50}
    if name == 'Customer': return {'id_student':int(r.get('id_student',0)),'gender':str(r.get('gender') or ''),'region':str(r.get('region') or ''),'highest_education':str(r.get('highest_education') or ''),'disability':str(r.get('disability') or '')}
    if name == 'CustomerBatch': return {'customers':['customer']*50}
    if name == 'EntitlementRequest': return {'customer_id':int(r.get('id_student',0))}
    if name == 'Entitlement': return {'id_student':int(r.get('id_student',0)),'date_registration':float(r.get('date_registration') or 0),'date_unregistration':float(r.get('date_unregistration') or 0)}
    if name == 'RevenueQuery': return {'region':str(r.get('region') or ''),'limit':50}
    if name == 'RegionRevenue': return {'region':str(r.get('region') or ''),'transactions':1,'revenue_total':float(r.get('score') or 0),'revenue_mean':float(r.get('score') or 0)}
    if name == 'RegionalRevenueReport': return {'regions':['region']*13,'transaction_total':173739,'revenue_total':13169342.0}
    if name == 'TransactionQuery': return {'customer_id':int(r.get('id_student',0)),'region':str(r.get('region') or ''),'limit':50}
    if name == 'Transaction': return {'id_assessment':int(r.get('id_assessment',0)),'id_student':int(r.get('id_student',0)),'assessment_type':str(r.get('assessment_type') or ''),'region':str(r.get('region') or ''),'score':float(r.get('score') or 0),'timestamp':str(r.get('date_submitted',0))}
    if name == 'TransactionList': return {'transactions':['transaction']*50}
    return {}

if __name__=='__main__':
    from contract import run
    run()
