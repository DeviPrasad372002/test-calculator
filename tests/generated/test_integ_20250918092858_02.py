import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import builtins
import importlib
import types
from types import SimpleNamespace

import pytest

# Attempt to import target modules from multiple possible locations.
try:
    import Calculator as Calc
    import SimpleCalculatorPyQt1 as GUI
except Exception:
    try:
        from target import Calculator as Calc
        from target import SimpleCalculatorPyQt1 as GUI
    except ImportError as e:
        pytest.skip(f"Required application modules not available: {e}", allow_module_level=True)
    except Exception:
        raise

# Ensure expected classes/objects exist in imported modules
if not hasattr(Calc, "Calculator") or not hasattr(Calc, "CalculatorError"):
    pytest.skip("Calculator or CalculatorError not found in Calculator module", allow_module_level=True)

Calculator = Calc.Calculator
CalculatorError = Calc.CalculatorError

if not (hasattr(GUI, "save_history") or hasattr(GUI, "MainWindow")):
    pytest.skip("Neither save_history nor MainWindow present in GUI module", allow_module_level=True)

@pytest.mark.parametrize(
    "a,b,divisor",
    [
        (2, 3, 3),
        (5, 4, 2),
        (0, 10, 5),
        (-2, 6, 3),
    ],
)
def test_calculator_multiply_then_divide_returns_expected_numeric_values(a, b, divisor):
    
    # Arrange
    calc = Calculator()

    # Act
    product = calc.multiply(a, b)
    result = calc.divide(product, divisor)

    # Assert
    # product should be exact multiplication
    assert product == a * b
    assert isinstance(product, (int, float))

    # division result should match Python division semantics (float when necessary)
    assert result == pytest.approx((a * b) / divisor)
    assert isinstance(result, (int, float))

def test_calculator_divide_by_zero_raises_calculator_error():
    
    # Arrange
    calc = Calculator()

    # Act / Assert
    with pytest.raises(CalculatorError):
        calc.divide(10, 0)

def _monkeypatch_qfiledialog_getsavefile(monkeypatch, gui_module, destination_path):
    """
    Helper to monkeypatch QFileDialog.getSaveFileName in whatever place GUI module likely references it.
    Returns None. This tries several likely attribute locations.
    """
    # Preferred: if GUI module exposes QFileDialog directly
    qfd = getattr(gui_module, "QFileDialog", None)
    if qfd is not None:
        monkeypatch.setattr(qfd, "getSaveFileName", lambda *a, **k: (str(destination_path), ""), raising=False)
        return

    # Next: if GUI imported QtWidgets as QtWidgets inside module
    qtwidgets = getattr(gui_module, "QtWidgets", None)
    if qtwidgets is not None and hasattr(qtwidgets, "QFileDialog"):
        monkeypatch.setattr(qtwidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(destination_path), ""), raising=False)
        return

    
    try:
        import PyQt5.QtWidgets as _qtwidgets  # type: ignore
    except Exception:
        # If PyQt5 not present, let higher-level logic handle using a simple function-based save_history call.
        return
    if hasattr(_qtwidgets, "QFileDialog"):
        monkeypatch.setattr(_qtwidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(destination_path), ""), raising=False)

def _call_save_history(gui_module, history_list):
    """
    Call save_history either as a standalone function or as a method on MainWindow instance.
    Returns nothing. Assumes QFileDialog.getSaveFileName has been monkeypatched to return a writable path.
    """
    # If there's a top-level function, prefer that and pass a simple object with a history attribute.
    if hasattr(gui_module, "save_history") and callable(gui_module.save_history):
        fake_self = SimpleNamespace(history=history_list)
        return gui_module.save_history(fake_self)

    
    MainWindow = getattr(gui_module, "MainWindow", None)
    if MainWindow is None:
        raise RuntimeError("No save_history function or MainWindow class to call")

    # Try to instantiate without arguments, fall back to None
    try:
        win = MainWindow()
    except TypeError:
        win = MainWindow(None)

    # Ensure the instance has a history attribute used by save_history
    setattr(win, "history", history_list)
    return win.save_history()

def test_integration_save_history_writes_file_and_contains_history_entries(tmp_path, monkeypatch):
    
    # Arrange
    # Prepare history entries based on using real Calculator.multiply to create an integration scenario
    calc = Calculator()
    a, b = 7, 8
    prod = calc.multiply(a, b)
    history_entries = [f"{a}*{b}={prod}", "extra entry: 1+1=2"]

    dest = tmp_path / "history_output.txt"
    _monkeypatch_qfiledialog_getsavefile(monkeypatch, GUI, dest)

    # Also ensure builtin open is not intercepted; we want a real file write to tmp_path
    # Act
    _call_save_history(GUI, history_entries)

    
    assert dest.exists(), "Expected history file to be created"
    content = dest.read_text(encoding="utf-8")
    for entry in history_entries:
        assert entry in content

def test_integration_save_history_handles_empty_history_by_creating_empty_file(tmp_path, monkeypatch):
    
    # Arrange
    empty_history = []
    dest = tmp_path / "empty_history.txt"
    _monkeypatch_qfiledialog_getsavefile(monkeypatch, GUI, dest)

    # Act
    _call_save_history(GUI, empty_history)

    # Assert
    assert dest.exists(), "Expected save_history to create a file even for empty history"
    content = dest.read_text(encoding="utf-8")
    # For empty history we expect either empty file or whitespace; ensure no unexpected content
    assert isinstance(content, str)
    assert content.strip() == "" or content == ""
