from __future__ import annotations
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from contracts import MESSAGES
from wire import proto_bytes, compare

def _pool():
    fd=descriptor_pb2.FileDescriptorProto(name='cma_dynamic.proto',package='cmaflow.v1',syntax='proto3')
    type_map={'int32':5,'int64':3,'double':1,'string':9,'bool':8}
    for m in MESSAGES:
        md=fd.message_type.add(); md.name=m.name
        for f in m.fields:
            fld=md.field.add(); fld.name=f.name; fld.number=f.number; fld.label=3 if f.repeated else 1; fld.type=type_map[f.typ]
    pool=descriptor_pool.DescriptorPool(); pool.Add(fd); return pool

def google_bytes(message,obj):
    pool=_pool(); cls=message_factory.GetMessageClass(pool.FindMessageTypeByName('cmaflow.v1.'+message)); msg=cls()
    for f in MESSAGES[[m.name for m in MESSAGES].index(message)].fields:
        v=obj.get(f.name)
        if v is None: continue
        vals=v if f.repeated else [v]
        field=getattr(msg,f.name)
        for x in vals:
            if f.repeated: field.append(x if isinstance(x,(str,int,float,bool)) else __import__('json').dumps(x,separators=(',',':')))
            else: setattr(msg,f.name,x)
    return msg.SerializeToString(deterministic=True)

def verify_against_google_protobuf(samples):
    failures=[]
    for name,obj in samples.items():
        ours=proto_bytes(name,obj); google=google_bytes(name,obj)
        if ours!=google: failures.append({'message':name,'ours':ours.hex(),'google':google.hex()})
    return {'installed':True,'cases':len(samples),'byte_identical':len(failures)==0,'failures':failures}

def run():
    from contracts import sample_for
    names=['Count','ChargeRequest','ChargeResult','Customer','MonetizationConfig','Entitlement','Transaction','RegionRevenue']
    samples={n:sample_for(n) for n in names}
    result=verify_against_google_protobuf(samples)
    print(f"google.protobuf installed: Yes · {result['cases']} byte-identical cases · passed: {result['byte_identical']}")
    if not result['byte_identical']: raise AssertionError(result['failures'])
    return result
if __name__=='__main__': run()
