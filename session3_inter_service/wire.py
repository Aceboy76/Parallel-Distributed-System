from __future__ import annotations
import json, struct
from contracts import message_map

def json_bytes(message: str, obj: dict) -> bytes:
    return json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

def varint(n: int) -> bytes:
    if n < 0: n &= (1 << 64) - 1
    out=bytearray()
    while n > 127: out.append((n & 127) | 128); n >>= 7
    out.append(n); return bytes(out)

def read_varint_from(data: bytes, pos: int):
    shift=0; n=0
    while pos < len(data):
        b=data[pos]; pos+=1; n |= (b & 127) << shift
        if b < 128: return n,pos
        shift += 7
        if shift > 70: raise ValueError('invalid varint')
    raise ValueError('truncated varint')

def encode_field(number: int, typ: str, value) -> bytes:
    if value is None: return b''
    if typ in ('int32','int64','bool'): return varint((1 if value else 0) if typ=='bool' else int(value))
    if typ == 'double': return struct.pack('<d', float(value))
    if typ == 'string':
        if not isinstance(value,str): value=json.dumps(value,separators=(',',':'),ensure_ascii=False)
        b=value.encode('utf-8'); return varint(len(b))+b
    raise ValueError(typ)

def proto_bytes(message: str, obj: dict) -> bytes:
    schema=message_map()[message]; out=bytearray()
    for f in schema.fields:
        value=obj.get(f.name)
        values=value if f.repeated and value is not None else ([value] if value is not None else [])
        for v in values:
            if v is None: continue
            # proto3 scalar defaults are omitted from the wire.
            if not f.repeated and ((f.typ in ('int32','int64','bool') and int(v)==0) or (f.typ=='double' and float(v)==0.0) or (f.typ=='string' and str(v)=='')): continue
            wt=0 if f.typ in ('int32','int64','bool') else (1 if f.typ=='double' else 2)
            out.extend(varint((f.number<<3)|wt)); out.extend(encode_field(f.number,f.typ,v))
    return bytes(out)

def _decode_scalar(typ, wt, data, pos):
    if typ in ('int32','int64','bool'):
        if wt != 0: raise ValueError('wire type mismatch')
        n,pos=read_varint_from(data,pos); return (bool(n) if typ=='bool' else n),pos
    if typ=='double':
        if wt != 1: raise ValueError('wire type mismatch')
        return struct.unpack('<d',data[pos:pos+8])[0],pos+8
    if typ=='string':
        if wt != 2: raise ValueError('wire type mismatch')
        n,pos=read_varint_from(data,pos); b=data[pos:pos+n]
        return b.decode('utf-8'),pos+n
    raise ValueError(typ)

def proto_decode(message: str, data: bytes) -> dict:
    schema=message_map()[message]; bynum={f.number:f for f in schema.fields}; out={}; pos=0
    while pos < len(data):
        tag,pos=read_varint_from(data,pos); num=tag>>3; wt=tag&7
        if num not in bynum:
            if wt==0: _,pos=read_varint_from(data,pos)
            elif wt==1: pos+=8
            elif wt==2: n,pos=read_varint_from(data,pos); pos+=n
            elif wt==5: pos+=4
            else: raise ValueError(f'unsupported unknown wire type {wt}')
            continue
        f=bynum[num]; value,pos=_decode_scalar(f.typ,wt,data,pos)
        if f.repeated: out.setdefault(f.name,[]).append(value)
        else: out[f.name]=value
    # Restore the nested logical structures represented as strings by the contract.
    for name in ('customers','transactions','configs'):
        if name in out:
            out[name]=[json.loads(x) if isinstance(x,str) and x[:1] in '[{' else x for x in out[name]]
    return out

def compare(message, obj):
    j=json_bytes(message,obj); p=proto_bytes(message,obj)
    return {'message':message,'json_bytes':len(j),'protobuf_bytes':len(p),'saved':len(j)-len(p),'reduction':(len(j)-len(p))/len(j)*100 if j else 0.0}
