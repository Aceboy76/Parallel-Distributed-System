from compose import reconcile

if __name__=='__main__':
    r=reconcile()
    print(f"regions={r['regions']}")
    print(f"transactions_db={r['transactions_db']}")
    print(f"transactions_session1={r['transactions_session1']}")
    print(f"transactions_session2={r['transactions_session2']}")
    print(f"aggregate_db={r['aggregate_db']:.2f}")
    print(f"aggregate_session1={r['aggregate_session1']:.2f}")
    print(f"aggregate_session2={r['aggregate_session2']:.2f}")
    print(f"max_count_difference={r['max_count_difference']}")
    print(f"aggregate_difference={r['aggregate_difference']:.3e}")
    print(f"tolerance={r['tolerance']}")
    print(f"passed={r['passed']}")
