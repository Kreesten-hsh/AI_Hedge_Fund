import pytest
import importlib

def test_python_version():
    import sys
    assert sys.version_info.major == 3
    assert sys.version_info.minor == 11

def test_openbb_import():
    openbb = importlib.import_module('openbb')
    assert openbb is not None

def test_qlib_import():
    try:
        qlib = importlib.import_module('qlib')
        assert qlib is not None
    except ImportError as e:
        pytest.xfail(f"Qlib non importable, connu et documenté sur certaines archs: {e}")

def test_vnpy_import():
    try:
        vnpy = importlib.import_module('vnpy')
        assert vnpy is not None
    except ImportError as e:
        pytest.xfail(f"VN.py non importable, connu et documenté: {e}")

def test_pandas_numpy():
    pd = importlib.import_module('pandas')
    np = importlib.import_module('numpy')
    assert pd is not None
    assert np is not None

def test_aegis_core_initialization():
    # Tester l'initialisation des composants clés d'Aegis
    from aegis_trade.engine.portfolio import PortfolioEngine
    engine = PortfolioEngine()
    assert engine is not None

def test_aegis_risk_initialization():
    from aegis_trade.engine.global_risk import GlobalRiskManager
    risk_manager = GlobalRiskManager()
    assert risk_manager is not None
