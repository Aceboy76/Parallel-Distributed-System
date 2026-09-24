from __future__ import annotations
import json, threading, time
from concurrent import futures
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contracts import SERVICES
from service_registry import ServiceRegistry
from services import ServiceFailure
from wire import json_bytes, proto_bytes, proto_decode, read_varint_from

_HTTP_SERVER=None; _HTTP_THREAD=None; _GRPC_SERVER=None
_REGISTRY=ServiceRegistry()

def _find_method(service, method):
    for name,req,res,kind in SERVICES[service]:
        if name==method: return req,res,kind
    raise KeyError(method)

def _error_payload(e):
    if isinstance(e, ServiceFailure): return {'_error':True,'code':e.code,'message':e.message,'details':json.dumps(e.details,separators=(',',':'))}
    if isinstance(e, TimeoutError): return {'_error':True,'code':'DEADLINE_EXCEEDED','message':str(e),'details':''}
    return {'_error':True,'code':'INTERNAL','message':str(e),'details':''}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def _send(self,status,body,ctype):
        self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path.startswith('/health'):
            self._send(200,b'{"ok":true}', 'application/json'); return
        self._send(404,b'{"_error":true,"code":"NOT_FOUND","message":"Route not found"}','application/json')
    def do_POST(self):
        parts=self.path.strip('/').split('/')
        if len(parts)<4 or parts[0]!='rpc': self._send(404,b'{"_error":true,"code":"NOT_FOUND","message":"RPC route not found"}','application/json'); return
        service,method,codec=parts[1:4]; streaming=len(parts)>4 and parts[4]=='stream'
        try: req_msg,res_msg,kind=_find_method(service,method)
        except KeyError:
            self._send(404,b'{"_error":true,"code":"NOT_FOUND","message":"RPC method not found"}','application/json'); return
        raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
        try:
            request=json.loads(raw.decode()) if codec=='json' else proto_decode(req_msg,raw)
            result=_REGISTRY.stream(service,method,request) if streaming else _REGISTRY.call(service,method,request)
            if streaming:
                if codec=='json':
                    body=b''.join(json_bytes(res_msg,x)+b'\n' for x in result); self._send(200,body,'application/x-ndjson')
                else:
                    chunks=[]
                    for x in result:
                        b=proto_bytes(res_msg,x); chunks.append(_varint(len(b))+b)
                    self._send(200,b''.join(chunks),'application/x-protobuf-stream')
                return
            if codec=='json': self._send(200,json_bytes(res_msg,result),'application/json')
            else: self._send(200,proto_bytes(res_msg,result),'application/x-protobuf')
        except Exception as e:
            err=_error_payload(e); body=json.dumps(err,separators=(',',':')).encode(); status=408 if err['code']=='DEADLINE_EXCEEDED' else (404 if err['code']=='NOT_FOUND' else 500); self._send(status,body,'application/json')

def _varint(n):
    out=bytearray()
    while n>127: out.append((n&127)|128); n>>=7
    out.append(n); return bytes(out)

def start_server(host='127.0.0.1', port=53210):
    global _HTTP_SERVER,_HTTP_THREAD
    if _HTTP_SERVER is not None: return _HTTP_SERVER
    _HTTP_SERVER=ThreadingHTTPServer((host,port),Handler); _HTTP_THREAD=threading.Thread(target=_HTTP_SERVER.serve_forever,daemon=True); _HTTP_THREAD.start(); return _HTTP_SERVER

def stop_server():
    global _HTTP_SERVER,_HTTP_THREAD
    if _HTTP_SERVER is not None: _HTTP_SERVER.shutdown(); _HTTP_SERVER.server_close(); _HTTP_SERVER=None; _HTTP_THREAD=None

def start_grpc_server(host='127.0.0.1', port=53211):
    global _GRPC_SERVER
    if _GRPC_SERVER is not None: return _GRPC_SERVER
    try: import grpc
    except ImportError as e: raise RuntimeError('grpcio is not installed') from e
    server=grpc.server(futures.ThreadPoolExecutor(max_workers=16))
    for service, methods in SERVICES.items():
        handlers={}
        for method,req,res,kind in methods:
            if kind=='server-streaming':
                def make_stream(s=service,m=method,req_msg=req,res_msg=res):
                    def fn(request, context):
                        try:
                            for item in _REGISTRY.stream(s,m,request,timeout=context.time_remaining()): yield item
                        except ServiceFailure as e:
                            context.set_code(getattr(grpc.StatusCode,e.code,grpc.StatusCode.INTERNAL)); context.set_details(e.message)
                    return fn
                handlers[method]=grpc.unary_stream_rpc_method_handler(make_stream(),request_deserializer=lambda b,r=req:proto_decode(r,b),response_serializer=lambda x,r=res:proto_bytes(r,x))
            else:
                def make_unary(s=service,m=method,req_msg=req,res_msg=res):
                    def fn(request, context):
                        try: return _REGISTRY.call(s,m,request,timeout=context.time_remaining())
                        except ServiceFailure as e:
                            context.set_code(getattr(grpc.StatusCode,e.code,grpc.StatusCode.INTERNAL)); context.set_details(e.message); return {}
                    return fn
                handlers[method]=grpc.unary_unary_rpc_method_handler(make_unary(),request_deserializer=lambda b,r=req:proto_decode(r,b),response_serializer=lambda x,r=res:proto_bytes(r,x))
        server.add_generic_rpc_handlers((grpc.method_handlers_generic_handler(f'cmaflow.v1.{service}',handlers),))
    server.add_insecure_port(f'{host}:{port}'); server.start(); _GRPC_SERVER=server; return server

def stop_grpc_server():
    global _GRPC_SERVER
    if _GRPC_SERVER is not None: _GRPC_SERVER.stop(0); _GRPC_SERVER=None
