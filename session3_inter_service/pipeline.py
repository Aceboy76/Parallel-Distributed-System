from __future__ import annotations
import json, traceback
from pathlib import Path
from contract import run as contract_run
from test_wire import run as wire_run
from benchmark import payload,latency,roundtrips,streaming
from adapter import compare_adapters,deadline_demo
from compose import compose,reconcile,summary
from services import transaction_sample,count_transactions
from config import OUT_SCHEMA

def typed_failure_demo():
    from transport import HttpTransport,make_stub,RpcException
    from service_host import start_server
    start_server(); codes={}
    for codec in ('json','proto'):
        stub=make_stub('CustomerService',HttpTransport(codec=codec))
        try: stub.call('GetCustomer',{'customer_id':999999999})
        except RpcException as e: codes[codec]=e.code
        else: raise AssertionError(f'Expected NOT_FOUND for {codec}')
    if codes['json'] != codes['proto']: raise AssertionError(codes)
    return {'json_code':codes['json'],'protobuf_code':codes['proto'],'typed':True}

def run_all(progress=None):
    def go(name,fn):
        if progress: progress(name,'running','')
        try:
            result=fn()
            if progress: progress(name,'passed',headline(name,result))
            return result
        except Exception as e:
            if progress: progress(name,'failed',str(e))
            raise
    go('Contract',contract_run); go('Wire format',wire_run); go('Serve',serve_info); go('Payload size',payload); go('Unary latency',latency); go('Round trips',roundtrips); go('Streaming',streaming); go('Adapter swap',compare_adapters); go('Deadline',deadline_demo); go('Typed failure',typed_failure_demo); go('Compose',compose); go('Reconcile',reconcile)
    return summary()

def serve_info():
    from service_host import start_server
    start_server(); sample=transaction_sample(1)
    data={'services':6,'host':'127.0.0.1:53210','grpc_host':'127.0.0.1:53211','sample_rows':len(sample),'transactions':count_transactions(),'transport_options':['in-process','http/json','http/proto','grpc/proto'],'server_started':True}
    OUT_SCHEMA.write_text(json.dumps(data,indent=2),encoding='utf-8'); return data

def headline(name,result):
    if name=='Contract': return f"{result['messages']} messages, {result['methods']} methods, {result['services']} services, {result['streaming_methods']} streaming"
    if name=='Serve': return f"{result['services']} services on {result['host']}"
    if name=='Wire format': return f"{result['cases']} protobuf cases · google.protobuf agreement: {result['byte_identical']}"
    if name=='Reconcile': return f"{result['regions']} regions · {result['transactions_db']:,} transactions · {result['aggregate_db']:,.2f} · {'PASSED' if result['passed'] else 'FAILED'}"
    if isinstance(result,list) and result and isinstance(result[0],list): return str(result[0][:4])
    if isinstance(result,dict) and 'json_code' in result: return f"JSON {result['json_code']}"
    return 'completed'
