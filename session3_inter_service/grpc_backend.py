"""Optional real grpcio backend for Session 3."""
from service_host import start_grpc_server, stop_grpc_server
from transport import GrpcTransport

def serve(host='127.0.0.1',port=53211): return start_grpc_server(host,port)

def smoke_test(target='127.0.0.1:53211'):
    t=GrpcTransport(target)
    from transport import make_stub
    s=make_stub('ConfigService',t)
    result=s.call('GetConfig',{'config_id':'oulad-score-proxy'})
    t.close(); return result

if __name__=='__main__':
    import time
    s=serve(); print('gRPC server listening on 127.0.0.1:53211'); time.sleep(3600)
