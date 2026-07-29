from aegis_trade.application.council.conflict_resolver import ConflictResolver

def test_conflict_resolver_no_conflict():
    resolver = ConflictResolver()
    multiplier, disagreement = resolver.resolve(0.8, 0.1)
    
    assert multiplier == 1.0
    assert disagreement == 0.125 # 0.1 / 0.8

def test_conflict_resolver_high_disagreement():
    resolver = ConflictResolver(high_disagreement_threshold=0.8, abort_threshold=0.95)
    # 0.8 / 0.9 = 0.888 > 0.8
    multiplier, disagreement = resolver.resolve(0.9, 0.8)
    
    assert multiplier == 0.25
    assert disagreement > 0.8

def test_conflict_resolver_abort():
    resolver = ConflictResolver(high_disagreement_threshold=0.8, abort_threshold=0.95)
    # 0.95 / 0.96 = 0.989 > 0.95
    multiplier, disagreement = resolver.resolve(0.96, 0.95)
    
    assert multiplier == 0.0
    assert disagreement > 0.95

def test_conflict_resolver_zeros():
    resolver = ConflictResolver()
    multiplier, disagreement = resolver.resolve(0.0, 0.0)
    assert multiplier == 0.0
    assert disagreement == 0.0
