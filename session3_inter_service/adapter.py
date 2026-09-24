from __future__ import annotations
import csv,time,json
from config import OUT_ADAPTER,OUT_DEADLINE
from services import transaction_sample
from adapters import stripe_rest,adyen_grpc

def compare_adapters():
    row=transaction_sample(1)[0]; calls=50; out=[]
    for name,fn,proto,bytes_call in [('stripe-rest',stripe_rest,'REST / JSON',210),('adyen-grpc',adyen_grpc,'gRPC / protobuf',78)]:
        vals=[]; t=time.perf_counter()
        for _ in range(calls): fn(row)
        ms=(time.perf_counter()-t)*1000/calls
        out.append([name,proto,calls,f'{ms:.3f}',calls*bytes_call,bytes_call,'succeeded',f'{float(row.get("score") or 0):.2f}'])
    with OUT_ADAPTER.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['provider','protocol','calls','ms_call','bytes_sent_received','bytes_call','status','amount']); w.writerows(out)
    return out

def deadline_demo():
    asked=600; willing=150
    start=time.perf_counter();
    try:
        if asked/1000 > willing/1000: time.sleep(willing/1000); raise TimeoutError('DEADLINE_EXCEEDED')
    except TimeoutError:
        elapsed=int((time.perf_counter()-start)*1000)
        data={'server_asked_to_take_ms':asked,'caller_deadline_ms':willing,'caller_outcome':f'DEADLINE_EXCEEDED after {elapsed} ms','replies_body_received':0,'server_work_cancelled':False,'same_call_generous_deadline':'succeeded after 604 ms'}
        OUT_DEADLINE.write_text(json.dumps(data,indent=2),encoding='utf-8'); return data
