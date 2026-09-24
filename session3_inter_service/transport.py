from __future__ import annotations
"""Transport-independent typed stubs for CMA-Flow Session 3.

The application talks to ServiceStub only.  The same service/method contract can
run in-process, over HTTP+JSON, over HTTP+protobuf-style bytes, or over real
grpcio when grpc is installed.
"""
import json
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from wire import json_bytes, proto_bytes, proto_decode

class RpcException(RuntimeError):
    def __init__(self, code: str, message: str, details=None):
        super().__init__(f"{code}: {message}")
        self.code, self.message, self.details = code, message, details or {}

class Transport:
    def call(self, service: str, method: str, request: dict, response: str, timeout: float | None = None):
        raise NotImplementedError
    def stream(self, service: str, method: str, request: dict, response: str, timeout: float | None = None):
        raise NotImplementedError
    def close(self):
        pass

@dataclass
class ServiceStub:
    transport: Transport
    service: str
    methods: dict
    def call(self, method: str, request: dict, timeout: float | None = None):
        if method not in self.methods: raise ValueError(f"Unknown method {self.service}.{method}")
        req, res, kind = self.methods[method]
        if kind != 'unary': raise ValueError(f"{method} is server-streaming")
        return self.transport.call(self.service, method, request, res, timeout=timeout)
    def stream(self, method: str, request: dict, timeout: float | None = None):
        if method not in self.methods: raise ValueError(f"Unknown method {self.service}.{method}")
        req, res, kind = self.methods[method]
        if kind != 'server-streaming': raise ValueError(f"{method} is not server-streaming")
        return self.transport.stream(self.service, method, request, res, timeout=timeout)

def make_stub(service: str, transport: Transport) -> ServiceStub:
    from contracts import SERVICES
    table = {m: (req, res, kind) for m, req, res, kind in SERVICES[service]}
    return ServiceStub(transport, service, table)

class InProcessTransport(Transport):
    def __init__(self, registry=None):
        if registry is None:
            from service_registry import ServiceRegistry
            registry = ServiceRegistry()
        self.registry = registry
    def call(self, service, method, request, response, timeout=None):
        return self.registry.call(service, method, request, timeout=timeout)
    def stream(self, service, method, request, response, timeout=None):
        return self.registry.stream(service, method, request, timeout=timeout)

class HttpTransport(Transport):
    def __init__(self, base_url='http://127.0.0.1:53210', codec='json'):
        self.base_url = base_url.rstrip('/')
        self.codec = codec
    def _request(self, service, method, request, response, timeout=None):
        body = json_bytes('Request', request) if self.codec == 'json' else proto_bytes(_request_message(service, method), request)
        path = f"/rpc/{service}/{method}/{self.codec}"
        req = Request(self.base_url + path, data=body, method='POST')
        req.add_header('Content-Type', 'application/json' if self.codec == 'json' else 'application/x-protobuf')
        try:
            with urlopen(req, timeout=timeout or 10) as r:
                raw = r.read(); status = r.status
                ctype = r.headers.get('Content-Type','')
        except HTTPError as e:
            raw = e.read(); status = e.code; ctype = e.headers.get('Content-Type','') if e.headers else ''
        if status >= 400:
            err = _decode_error(raw, ctype)
            raise RpcException(err.get('code','INTERNAL'), err.get('message','RPC failed'), err)
        return _decode_response(response, raw, self.codec, ctype)
    def call(self, service, method, request, response, timeout=None):
        return self._request(service, method, request, response, timeout)
    def stream(self, service, method, request, response, timeout=None):
        # NDJSON for JSON and length-delimited protobuf messages for binary.
        body = json_bytes(_request_message(service, method), request) if self.codec == 'json' else proto_bytes(_request_message(service, method), request)
        path = f"/rpc/{service}/{method}/{self.codec}/stream"
        req = Request(self.base_url + path, data=body, method='POST')
        req.add_header('Content-Type','application/json' if self.codec == 'json' else 'application/x-protobuf')
        with urlopen(req, timeout=timeout or 30) as r:
            raw = r.read()
        if self.codec == 'json':
            for line in raw.splitlines():
                if line.strip(): yield json.loads(line)
        else:
            # Each record is: varint length + protobuf message.
            from wire import read_varint_from
            pos=0
            while pos < len(raw):
                n,pos=read_varint_from(raw,pos); chunk=raw[pos:pos+n]; pos+=n
                yield proto_decode(response,chunk)

class GrpcTransport(Transport):
    """Real grpcio generic transport; no generated *_pb2 files are required."""
    def __init__(self, target='127.0.0.1:53211', channel=None):
        try:
            import grpc
        except ImportError as e:
            raise RuntimeError('grpcio is not installed; install grpcio to use GrpcTransport') from e
        self.grpc = grpc
        self.channel = channel or grpc.insecure_channel(target)
    def call(self, service, method, request, response, timeout=None):
        path=f"/cmaflow.v1.{service}/{method}"
        rpc=self.channel.unary_unary(path, request_serializer=lambda x: proto_bytes(_request_message(service,method),x), response_deserializer=lambda b: proto_decode(response,b))
        try: return rpc(request, timeout=timeout)
        except self.grpc.RpcError as e: raise RpcException(e.code().name, e.details() or '') from e
    def stream(self, service, method, request, response, timeout=None):
        path=f"/cmaflow.v1.{service}/{method}"
        rpc=self.channel.unary_stream(path, request_serializer=lambda x: proto_bytes(_request_message(service,method),x), response_deserializer=lambda b: proto_decode(response,b))
        try:
            for item in rpc(request, timeout=timeout): yield item
        except self.grpc.RpcError as e: raise RpcException(e.code().name, e.details() or '') from e
    def close(self): self.channel.close()

def _request_message(service, method):
    from contracts import SERVICES
    for name, req, res, kind in SERVICES[service]:
        if name == method: return req
    raise KeyError(method)

def _decode_response(message, raw, codec, ctype=''):
    if codec == 'json':
        obj=json.loads(raw.decode('utf-8') or '{}')
        if isinstance(obj, dict) and obj.get('_error'): raise RpcException(obj['code'],obj['message'],obj)
        return obj
    return proto_decode(message, raw)

def _decode_error(raw, ctype):
    try: return json.loads(raw.decode('utf-8'))
    except Exception: return {'code':'INTERNAL','message':raw.decode('utf-8','replace')}
