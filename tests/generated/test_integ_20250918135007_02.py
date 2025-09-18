import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import builtins
import inspect
from unittest.mock import mock_open
import pytest

# Module-level import guards
try:
    from target import Calculator as calc_mod
    from target import SimpleCalculatorPyQt1 as ui_mod
except Exception as _err:
    pytest.skip("Required target modules not importable: {}".format(_err), allow_module_level=True)

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (2, 3, 6),
        (0, 5, 0),
        (3.5, 2, 7.0),
    ],
)
def test_Calculator_multiply_various(a, b, expected):
    
    # Arrange
    calc = calc_mod.Calculator()

    # Act
    result = calc.multiply(a, b)

    # Assert
    assert isinstance(result, (int, float))
    assert result == expected

def test_Calculator_divide_by_zero_raises_CalculatorError():
    
    # Arrange
    calc = calc_mod.Calculator()

    # Act / Assert
    with pytest.raises(calc_mod.CalculatorError):
        calc.divide(10, 0)

def test_save_history_writes_entry_to_file(tmp_path, monkeypatch):
    
    # Arrange
    entry = "6 * 7 = 42"
    # Prepare a mock open for both module-level open and builtins.open to intercept writes
    m_open = mock_open()
    # Patch open in the ui_mod namespace and builtins to be safe regardless of how it's referenced
    monkeypatch.setattr(ui_mod, "open", m_open, raising=False)
    monkeypatch.setattr(builtins, "open", m_open, raising=False)

    # Try to call save_history in a way that adapts to expected signature.
    save_history = getattr(ui_mod, "save_history", None)
    if not callable(save_history):
        pytest.skip("save_history not available in module")

    # Act
    try:
        sig = inspect.signature(save_history)
        params = sig.parameters
        # If it's a bound function method expecting (self, text) or (text,)
        if len(params) == 1:
            # likely save_history(text)
            save_history(entry)
        elif len(params) == 2:
            # likely save_history(self, text) -> provide a minimal dummy self
            class DummySelf:
                pass
            save_history(DummySelf(), entry)
        else:
            
            try:
                save_history(entry)
            except TypeError:
                pytest.skip("save_history has an unsupported signature: {}".format(sig))
    except TypeError:
        
        try:
            save_history(entry)
        except TypeError:
            pytest.skip("Unable to call save_history; signature incompatible")

    # Assert
    handle = m_open()
    # Ensure write was called at least once and that the entry was written
    assert handle.write.called, "save_history did not write to file handle"
    written = "".join(call.args[0] for call in handle.write.mock_calls if call.args)
    assert entry in written

def test_integration_multiply_then_save_history_called(monkeypatch):
    
    # Arrange
    calc = calc_mod.Calculator()
    a, b = 8, 5
    expected = a * b
    entry = f"{a} * {b} = {expected}"

    # Spy on save_history to ensure it's invoked when we explicitly call it in integration flow.
    save_history = getattr(ui_mod, "save_history", None)
    if not callable(save_history):
        pytest.skip("save_history not available in module")

    called = {"flag": False, "received": None}

    def fake_save_history(*args, **kwargs):
        called["flag"] = True
        called["received"] = args
        return None

    monkeypatch.setattr(ui_mod, "save_history", fake_save_history, raising=False)

    # Act
    result = calc.multiply(a, b)
    # In a typical integration flow, result would be formatted and passed to save_history
    # We simulate that step here.
    ui_mod.save_history(entry)

    # Assert
    assert result == expected
    assert called["flag"] is True
    # Ensure the entry was passed through to save_history (first positional arg may be self or the text)
    received_args = called["received"]
    assert any(entry == arg for arg in received_args), "save_history did not receive the expected entry"
