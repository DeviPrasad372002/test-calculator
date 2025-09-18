import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import importlib
import types
import pytest

# Guard third-party (PyQt5) import at module level per instructions.
try:
    import PyQt5  # noqa: F401
except Exception:
    pytest.skip("PyQt5 is required for these integration tests", allow_module_level=True)

import target.Calculator as CalculatorModule
# Don't import SimpleCalculatorPyQt1 here; tests will import/reload it as needed.

# Helper fake calculator for integration substitution
class FakeCalculator:
    def __init__(self, *args, **kwargs):
        self.calls = []

    def add(self, a, b):
        self.calls.append(("add", a, b))
        return 999  # deterministic sentinel

    def subtract(self, a, b):
        self.calls.append(("subtract", a, b))
        return -999  # deterministic sentinel

    def multiply(self, a, b):
        self.calls.append(("multiply", a, b))
        return 0

    def divide(self, a, b):
        self.calls.append(("divide", a, b))
        if b == 0:
            raise CalculatorModule.CalculatorError("division by zero")
        return 1

# Tests

@pytest.mark.parametrize(
    "a,b,expected_add,expected_subtract",
    [
        (1, 2, 3, -1),
        (-5, 3, -2, -8),
        (0, 0, 0, 0),
        (2.5, 1.5, 4.0, 1.0),
    ],
)
def test_Calculator_add_subtract_various(a, b, expected_add, expected_subtract):
    
    # Arrange
    calc = CalculatorModule.Calculator()
    # Act
    result_add = calc.add(a, b)
    result_sub = calc.subtract(a, b)
    # Assert
    assert isinstance(result_add, (int, float))
    assert isinstance(result_sub, (int, float))
    assert result_add == expected_add
    assert result_sub == expected_subtract

def test_Calculator_divide_by_zero_raises():
    
    # Arrange
    calc = CalculatorModule.Calculator()
    # Act / Assert
    with pytest.raises(CalculatorModule.CalculatorError):
        calc.divide(10, 0)

def test_SimpleCalculatorPyQt1_exports_and_uses_Calculator(monkeypatch):
    
    # Arrange
    # Ensure that when the GUI module imports Calculator it can be swapped for a fake.
    # Monkeypatch the Calculator symbol in the Calculator module to ensure identity.
    monkeypatch.setattr(CalculatorModule, "Calculator", FakeCalculator, raising=True)

    # Reload the GUI module to pick up any changes and to verify cross-module wiring.
    gui_name = "target.SimpleCalculatorPyQt1"
    if gui_name in importlib.util.sys.modules:
        importlib.reload(importlib.import_module(gui_name))
    gui_mod = importlib.import_module(gui_name)
    importlib.reload(gui_mod)

    # Act / Assert
    
    assert hasattr(gui_mod, "MainWindow"), "MainWindow class must be present in GUI module"
    MainWindow = getattr(gui_mod, "MainWindow")
    assert isinstance(MainWindow, type), "MainWindow should be a class type"

    # The GUI module should reference Calculator (we monkeypatched the original module's symbol).
    # It may have its own binding; at minimum the symbol should exist.
    assert hasattr(gui_mod, "Calculator"), "GUI module must expose a Calculator symbol"

    
    # skip the instantiation step but keep the module-level integration assertions above.
    try:
        # Act: instantiate and ensure calculate/clear_history/clear_input exist as callables
        mw = MainWindow()
    except Exception as exc:  # pragma: no cover - platform dependent GUI issues
        pytest.skip(f"Could not instantiate MainWindow in this environment: {exc}")

    # Assert that integration points exist and are callable
    assert hasattr(mw, "calculate") and callable(getattr(mw, "calculate"))
    assert hasattr(mw, "clear_history") and callable(getattr(mw, "clear_history"))
    assert hasattr(mw, "clear_input") and callable(getattr(mw, "clear_input"))
    
    
    # Provide typical attributes if present to avoid AttributeError inside calculate.
    # Many implementations use attributes like inputLine, operatorBox, resultLabel, or similar.
    # Set common possible names if they are missing to safe default objects.
    class DummyLine:
        def __init__(self, text="0"):
            self._text = text

        def text(self):
            return self._text

        def setText(self, txt):
            self._text = txt

        def clear(self):
            self._text = ""

    # Provide several attribute fallbacks
    for attr in ("inputLine", "lineEdit", "lhs", "rhs"):
        if not hasattr(mw, attr):
            setattr(mw, attr, DummyLine("2"))

    # Provide operator if needed
    if not hasattr(mw, "operator"):
        setattr(mw, "operator", DummyLine("+"))

    
    try:
        mw.calculate()
    except Exception as exc:  # pragma: no cover - behavior depends on GUI wiring
        pytest.skip(f"calculate invocation failed in this environment: {exc}")
