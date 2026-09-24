from __future__ import annotations
import time
from services import CustomerService, ConfigService, EntitlementService, TransactionService, RevenueService, ChargeService

class ServiceRegistry:
    """Runtime service boundary registry used by in-process and network hosts."""
    def __init__(self):
        self.services = {
            'CustomerService': CustomerService(),
            'ConfigService': ConfigService(),
            'EntitlementService': EntitlementService(),
            'TransactionService': TransactionService(),
            'RevenueService': RevenueService(),
            'ChargeService': ChargeService(),
        }
    def call(self, service, method, request, timeout=None):
        started=time.perf_counter()
        if timeout is not None and timeout <= 0: raise TimeoutError('DEADLINE_EXCEEDED')
        
        target = ''.join('_'+c.lower() if c.isupper() else c for c in method).lstrip('_')
        return getattr(self.services[service], target)(request, deadline=timeout, started=started)
    def stream(self, service, method, request, timeout=None):
        started=time.perf_counter()
        
        target = ''.join('_'+c.lower() if c.isupper() else c for c in method).lstrip('_')
        yield from getattr(self.services[service], target)(request, deadline=timeout, started=started)
