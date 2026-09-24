from __future__ import annotations
from transport import make_stub, HttpTransport, GrpcTransport, RpcException

class PaymentProviderAdapter:
    def charge(self, amount_cents, customer_id, currency='SCORE', idempotency_key='demo', delay_ms=0): raise NotImplementedError

class RestPaymentAdapter(PaymentProviderAdapter):
    def __init__(self, base_url='http://127.0.0.1:53210'):
        self.transport=HttpTransport(base_url,'json'); self.stub=make_stub('ChargeService',self.transport); self.provider='stripe-rest'
    def charge(self, amount_cents, customer_id, currency='SCORE', idempotency_key='demo', delay_ms=0):
        result=self.stub.call('Charge',{'amount_cents':amount_cents,'customer_id':str(customer_id),'currency':currency,'idempotency_key':idempotency_key,'delay_ms':delay_ms})
        result['provider']=self.provider; return result

class GrpcPaymentAdapter(PaymentProviderAdapter):
    def __init__(self, target='127.0.0.1:53211'):
        self.transport=GrpcTransport(target); self.stub=make_stub('ChargeService',self.transport); self.provider='adyen-grpc'
    def charge(self, amount_cents, customer_id, currency='SCORE', idempotency_key='demo', delay_ms=0):
        result=self.stub.call('Charge',{'amount_cents':amount_cents,'customer_id':str(customer_id),'currency':currency,'idempotency_key':idempotency_key,'delay_ms':delay_ms})
        result['provider']=self.provider; return result

# Backward-compatible functions used by earlier scripts.
def stripe_rest(row): return {'status':'succeeded','amount':float(row.get('score') or 0),'provider':'stripe-rest'}
def adyen_grpc(row): return {'status':'succeeded','amount':float(row.get('score') or 0),'provider':'adyen-grpc'}

def checkout(payment_adapter, amount_cents, customer_id):
    """Caller-facing seam: checkout does not know REST, gRPC, JSON, or protobuf."""
    return payment_adapter.charge(amount_cents, customer_id, idempotency_key=f'checkout-{customer_id}')
