from __future__ import annotations
import argparse
from pipeline import run_all,typed_failure_demo

def main():
    ap=argparse.ArgumentParser(description='CMA-Flow Session 3 inter-service communication')
    ap.add_argument('--stage',choices=['all','contract','wire','payload','latency','roundtrips','streaming','adapter','deadline','typed-failure','compose','reconcile','serve'],default='all')
    a=ap.parse_args()
    if a.stage=='all': run_all(lambda n,s,h: print(f'{n:18} {s:7} {h}')); return
    from contract import run as c
    from test_wire import run as wire
    from benchmark import payload,latency,roundtrips,streaming
    from adapter import compare_adapters,deadline_demo
    from compose import compose,reconcile
    from pipeline import serve_info
    {'contract':c,'wire':wire,'payload':payload,'latency':latency,'roundtrips':roundtrips,'streaming':streaming,'adapter':compare_adapters,'deadline':deadline_demo,'typed-failure':typed_failure_demo,'compose':compose,'reconcile':reconcile,'serve':serve_info}[a.stage]()
if __name__=='__main__': main()
