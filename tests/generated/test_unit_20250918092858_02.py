import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import inspect
import types
from unittest.mock import mock_open, patch

import pytest

try:
    import PyQt5  # noqa: F401
except Exception:
    pytest.skip("PyQt5 not available, skipping GUI-related tests", allow_module_level=True)

# Import target modules; skip if missing
try:
    import Calculator
except Exception:
    pytest.skip("Calculator module not importable", allow_module_level=True)

try:
    import SimpleCalculatorPyQt1
except Exception:
    pytest.skip("SimpleCalculatorPyQt1 module not importable", allow_module_level=True)

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (2, 3, 6),
        (0, 5, 0),
        (-4, 5, -20),
        (2.5, 2, 5.0),
        (-3.0, -2.0, 6.0),
    ],
)
def test_multiply_various_inputs_returns_expected(a, b, expected):
    
    # Arrange
    calc = Calculator.Calculator()
    # Act
    result = calc.multiply(a, b)
    # Assert
    assert result == expected
    assert isinstance(result, (int, float))

@pytest.mark.parametrize(
    "numerator,denominator,expected",
    [
        (10, 2, 5),
        (7, 2, 3.5),
        (-9, 3, -3),
        (5.0, 2.5, 2.0),
    ],
)
def test_divide_regular_cases(numerator, denominator, expected):
    
    # Arrange
    calc = Calculator.Calculator()
    # Act
    result = calc.divide(numerator, denominator)
    # Assert
    assert result == expected
    assert isinstance(result, (int, float))

def test_divide_by_zero_raises_calculator_error():
    
    # Arrange
    calc = Calculator.Calculator()
    # Act / Assert
    with pytest.raises(Calculator.CalculatorError):
        calc.divide(1, 0)

def test_save_history_calls_open_and_writes(tmp_path, monkeypatch):
    
    # Arrange
    module = SimpleCalculatorPyQt1
    candidate = None
    is_method = False

    
    if hasattr(module, "save_history") and callable(getattr(module, "save_history")):
        candidate = getattr(module, "save_history")
        is_method = False
    elif hasattr(module, "MainWindow"):
        mw = getattr(module, "MainWindow")
        if hasattr(mw, "save_history"):
            # unbound function (function object from class)
            candidate = getattr(mw, "save_history")
            is_method = True

    if candidate is None:
        pytest.skip("No save_history callable found in module")

    out_file = tmp_path / "history.txt"
    m = mock_open()
    monkeypatch.setattr("builtins.open", m)

    # Prepare a flexible fake self that covers common implementations:
    # - self.history as list of strings
    # - self.ui.historyList with count() and item(i).text() or .text property
    fake_self = types.SimpleNamespace()
    fake_self.history = ["1 + 1 = 2", "2 * 3 = 6"]

    class FakeItem:
        def __init__(self, txt):
            self._txt = txt
        def text(self):
            return self._txt

    class FakeList:
        def __init__(self, items):
            self._items = items
        def count(self):
            return len(self._items)
        def item(self, i):
            return FakeItem(self._items[i])

    fake_self.ui = types.SimpleNamespace(historyList=FakeList(fake_self.history))

    # Act: try different plausible signatures
    called = False
    call_exceptions = []
    # candidate could be function(path) or method(self, path) or method(self) (using internal default path)
    try:
        if is_method:
            # try common signature: save_history(self, path)
            sig = inspect.signature(candidate)
            if len(sig.parameters) == 2:
                candidate(fake_self, str(out_file))
            elif len(sig.parameters) == 1:
                # maybe method only needs self and uses dialog to pick path; call and hope it writes default
                candidate(fake_self)
            else:
                candidate(fake_self, str(out_file))
        else:
            sig = inspect.signature(candidate)
            if len(sig.parameters) == 1:
                candidate(str(out_file))
            elif len(sig.parameters) == 0:
                candidate()
            else:
                # try passing path as first arg
                candidate(str(out_file))
        called = True
    except Exception as e:
        call_exceptions.append(e)
        called = False

    # Assert that open was called with the target path and that write was invoked
    assert called, f"save_history candidate could not be invoked: {call_exceptions}"
    # There should be at least one call to open; find one that mentions our filename
    opens = [c for c in m.call_args_list if str(out_file) in (c[0][0] if c[0] else "")]
    assert opens, f"save_history did not call open with path {out_file}"
    # Ensure write was called on file handle returned by open
    handle = m()
    assert handle.write.called, "save_history did not write to the opened file"
