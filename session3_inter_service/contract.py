from __future__ import annotations
import json
from pathlib import Path
from contracts import MESSAGES,SERVICES,field_count,method_count,message_map
from config import OUT_CONTRACT

def render_proto():
    lines=['syntax = "proto3";','package cmaflow.v1;','']
    for m in MESSAGES:
        lines.append(f'message {m.name} {{')
        for f in m.fields: lines.append(f'  {"repeated " if f.repeated else ""}{f.typ} {f.name} = {f.number};')
        lines.append('}\n')
    for service,methods in SERVICES.items():
        lines.append(f'service {service} {{')
        for name,req,res,kind in methods:
            suffix=f' returns (stream {res})' if kind=='server-streaming' else f' returns ({res})'
            lines.append(f'  rpc {name} ({req}){suffix};')
        lines.append('}\n')
    return '\n'.join(lines)

def verify_against_proto(proto_path=None):
    proto_path=Path(proto_path or Path(__file__).with_name('cma.proto'))
    if not proto_path.exists(): return {'ok':False,'reason':'cma.proto missing'}
    actual=proto_path.read_text(encoding='utf-8').strip(); expected=render_proto().strip()
    return {'ok':actual==expected,'reason':'match' if actual==expected else 'contracts.py differs from cma.proto'}

def run():
    Path(__file__).with_name('cma.proto').write_text(render_proto(),encoding='utf-8')
    sync=verify_against_proto()
    data={'messages':len(MESSAGES),'fields':field_count(),'services':len(SERVICES),'methods':method_count(),'streaming_methods':sum(1 for ms in SERVICES.values() for x in ms if x[3]!='unary'),'contracts_in_sync':sync['ok'],'verify_against_proto':sync,'services':{k:[{'method':x[0],'request':x[1],'response':x[2],'kind':x[3]} for x in v] for k,v in SERVICES.items()}}
    OUT_CONTRACT.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(f"{data['messages']} messages, {data['fields']} fields, {len(SERVICES)} services, {data['methods']} methods ({data['streaming_methods']} server-streaming) · contracts.py in sync with cma.proto: {data['contracts_in_sync']}")
    return data
if __name__=='__main__': run()
