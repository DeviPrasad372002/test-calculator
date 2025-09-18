import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import inspect
import pytest

try:
    from target import Calculator as CalcMod
    from target import SimpleCalculatorPyQt1 as AppMod
except ImportError as e:
    pytest.skip(f"Required target modules not available: {e}", allow_module_level=True)

class _FakeHistory:
    def __init__(self, initial=""):
        self._text = initial

    def clear(self):
        self._text = ""

    def toPlainText(self):
        return self._text

    def setPlainText(self, txt):
        self._text = txt

    def append(self, txt):
        if self._text:
            self._text += "\n" + txt
        else:
            self._text = txt

class _FakeInput:
    def __init__(self, text=""):
        self._text = text

    def clear(self):
        self._text = ""

    def text(self):
        return self._text

    def setText(self, txt):
        self._text = txt

@pytest.mark.parametrize(
    "a,b,method_name,expected",
    [
        (1, 2, "add", 3),
        (5, 3, "subtract", 2),
        (4, 6, "multiply", 24),
        (20, 4, "divide", 5),
    ],
)
def test_Calculator_arithmetic_operations(a, b, method_name, expected):
    
    # Arrange
    Calculator = getattr(CalcMod, "Calculator", None)
    assert Calculator is not None and inspect.isclass(Calculator), "Calculator class must be present"

    calc = Calculator()

    # Act
    method = getattr(calc, method_name)
    result = method(a, b)

    # Assert
    assert isinstance(result, (int, float)), "result must be numeric"
    assert result == expected

def test_Calculator_divide_by_zero_raises():
    
    CalculatorError = getattr(CalcMod, "CalculatorError", None)
    Calculator = getattr(CalcMod, "Calculator", None)
    assert CalculatorError is not None, "CalculatorError must be defined"
    assert Calculator is not None and inspect.isclass(Calculator), "Calculator class must be present"

    calc = Calculator()

    with pytest.raises(CalculatorError):
        calc.divide(10, 0)

def test_MainWindow_clear_history_clears_history_display():
    
    MainWindow = getattr(AppMod, "MainWindow", None)
    assert MainWindow is not None and inspect.isclass(MainWindow), "MainWindow class must be present"

    # Create instance without running __init__
    win = object.__new__(MainWindow)

    # Arrange: attach fake history with existing content
    win.history_display = _FakeHistory(initial="previous result")
    assert win.history_display.toPlainText() == "previous result"

    # Act
    # Use clear_history if present
    clear_history = getattr(win, "clear_history", None)
    assert callable(clear_history), "MainWindow.clear_history must be callable"
    clear_history()

    # Assert
    assert win.history_display.toPlainText() == "", "History display should be empty after clear_history"

def test_MainWindow_clear_input_clears_input_field():
    
    MainWindow = getattr(AppMod, "MainWindow", None)
    assert MainWindow is not None and inspect.isclass(MainWindow), "MainWindow class must be present"

    win = object.__new__(MainWindow)

    # Arrange: attach fake input with content
    win.input_field = _FakeInput(text="12345")
    assert win.input_field.text() == "12345"

    # Act
    clear_input = getattr(win, "clear_input", None)
    assert callable(clear_input), "MainWindow.clear_input must be callable"
    clear_input()

    # Assert
    assert win.input_field.text() == "", "Input field should be empty after clear_input"

def test_MainWindow_calculate_raises_when_widgets_missing():
    
    MainWindow = getattr(AppMod, "MainWindow", None)
    assert MainWindow is not None and inspect.isclass(MainWindow), "MainWindow class must be present"

    # Create instance without widgets deliberately to simulate incomplete state
    win = object.__new__(MainWindow)

    calculate = getattr(win, "calculate", None)
    assert callable(calculate), "MainWindow.calculate must be callable"

    
    with pytest.raises(AttributeError):
        calculate()
