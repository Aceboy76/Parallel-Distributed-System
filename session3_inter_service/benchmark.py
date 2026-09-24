from __future__ import annotations
import csv,time,json
from urllib.request import urlopen
from config import *
from contracts import sample_for,message_map
from wire import compare,json_bytes,proto_bytes
from services import transaction_sample,transactions,customers
from transport import InProcessTransport,HttpTransport,make_stub

def write_csv(path,headers,rows):
    with path.open('w',newline='',encoding='utf-8') as f: csv.writer(f).writerows([headers,*rows])

def payload():
    row=transaction_sample(1)[0]; rows=[]
    for name in ['ChargeRequest','ChargeResult','Customer','MonetizationConfig','Entitlement','Transaction','RegionRevenue','RegionalRevenueReport','CustomerBatch']:
        c=compare(name,sample_for(name,row)); rows.append([c['message'],len(message_map()[name].fields),c['json_bytes'],c['protobuf_bytes'],c['saved'],f"{c['reduction']:.1f}"])
    write_csv(OUT_PAYLOAD,['message','fields','json_bytes','protobuf_bytes','saved','reduction_pct'],rows); return rows

def wire_check():
    row=transaction_sample(1)[0]; return compare('Transaction',sample_for('Transaction',row))

def _http_call(codec):
    path=f'http://127.0.0.1:53210/rpc/TransactionService/CountTransactions/{codec}'
    req=json_bytes('Empty',{}) if codec=='json' else proto_bytes('Empty',{})
    from urllib.request import Request
    r=Request(path,data=req,method='POST'); r.add_header('Content-Type','application/json' if codec=='json' else 'application/x-protobuf')
    return urlopen(r,timeout=3).read()

def latency():
    from service_host import start_server,start_grpc_server
    start_server(); row=transaction_sample(1)[0]; obj=sample_for('Transaction',row); calls=200; warmups=20
    inproc=make_stub('TransactionService',InProcessTransport()); inproc_req={'customer_id':obj['id_student'],'limit':1}
    paths=[('in-process','none',lambda:inproc.call('ListTransactions',inproc_req),0)]
    for codec in ('json','proto'): paths.append((f'http/{codec}',codec,lambda c=codec:_http_call(c),len(json_bytes('Transaction',obj)) if codec=='json' else len(proto_bytes('Transaction',obj))))
    results=[]
    for transport,codec,fn,bytes_call in paths:
        for _ in range(warmups): fn()
        samples=[]
        for _ in range(calls):
            t=time.perf_counter(); fn(); samples.append((time.perf_counter()-t)*1000)
        samples.sort(); med=samples[len(samples)//2]
        results.append([transport,codec,calls,f'{med:.4f}',f'{1000/med:.0f}',bytes_call,warmups])
    # Optional real grpc backend.
    try:
        from service_host import start_grpc_server
        start_grpc_server(); from transport import GrpcTransport
        g=make_stub('TransactionService',GrpcTransport());
        for _ in range(warmups): g.call('ListTransactions',inproc_req)
        ss=[]
        for _ in range(calls):
            t=time.perf_counter(); g.call('ListTransactions',inproc_req); ss.append((time.perf_counter()-t)*1000)
        ss.sort(); med=ss[len(ss)//2]; results.append(['grpc','proto',calls,f'{med:.4f}',f'{1000/med:.0f}',len(proto_bytes('Transaction',obj)),warmups])
    except Exception: pass
    write_csv(OUT_LATENCY,['transport','codec','calls','median_ms','calls_sec','bytes_call','warmup_discarded'],results); return results

def roundtrips():
    rows=transaction_sample(DEFAULT_ROUND_TRIP_ROWS); ids=[]
    for r in rows:
        sid=int(r['id_student'])
        if sid not in ids: ids.append(sid)
        if len(ids)>=DEFAULT_ROUND_TRIP_ROWS: break
    ids=ids[:DEFAULT_ROUND_TRIP_ROWS]
    inproc=make_stub('CustomerService',InProcessTransport())
    results=[]
    for codec in ('json','proto'):
        # Serialization is kept constant; DB work is one batch query versus N point queries.
        t=time.perf_counter(); rs=customers(ids); payload=[sample_for('Customer',r) for r in rs];
        if codec=='json': json_bytes('CustomerBatch',{'customers':payload})
        else: proto_bytes('CustomerBatch',{'customers':payload})
        bat=(time.perf_counter()-t)*1000
        t=time.perf_counter();
        for sid in ids:
            r=customers([sid]); obj=sample_for('Customer',r[0]) if r else {}
            if codec=='json': json_bytes('Customer',obj)
            else: proto_bytes('Customer',obj)
        singles=(time.perf_counter()-t)*1000
        results.append([codec,len(ids),1,f'{bat:.3f}',len(ids),f'{singles:.3f}',f'{singles/bat:.1f}x' if bat else '0x',len(ids)-1])
    write_csv(OUT_ROUNDTRIP,['codec','rows','batched_calls','batched_ms','single_calls','single_ms','speedup','round_trips_saved'],results); return results

def streaming():
    rows=transactions(limit=DEFAULT_STREAM_ROWS); out=[]
    for codec in ('json','proto'):
        encode=json_bytes if codec=='json' else proto_bytes
        t=time.perf_counter(); [encode('Transaction',sample_for('Transaction',r)) for r in rows]; unary=(time.perf_counter()-t)*1000
        stream_start=time.perf_counter(); first=None
        for r in rows:
            encode('Transaction',sample_for('Transaction',r))
            if first is None: first=(time.perf_counter()-stream_start)*1000
        stream_total=(time.perf_counter()-stream_start)*1000
        out.append([codec,len(rows),f'{unary:.3f}',f'{stream_total:.3f}',f'{first or 0:.3f}',f'{unary/(first or 1):.1f}x'])
    write_csv(OUT_STREAMING,['codec','rows','unary_total_ms','stream_total_ms','first_message_ms','earlier_by'],out); return out

if __name__=='__main__':
    print('payload:', payload())
    print('latency:', latency())
    print('roundtrips:', roundtrips())
    print('streaming:', streaming())
