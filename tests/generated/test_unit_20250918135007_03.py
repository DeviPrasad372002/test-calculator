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
import types
import pytest

# Guard third-party imports
try:
    import PyQt5  # noqa: F401
except ImportError:
    pytest.skip("PyQt5 is required for these tests", allow_module_level=True)

# Import target modules; skip if not present
try:
    import Calculator as calc_mod
except ImportError:
    pytest.skip("Calculator module not found", allow_module_level=True)

try:
    import SimpleCalculatorPyQt1 as app_mod
except ImportError:
    pytest.skip("SimpleCalculatorPyQt1 module not found", allow_module_level=True)

# Simple test doubles for widget-like behavior
class DummyInput:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text

    def setText(self, txt):
        self._text = txt

    def clear(self):
        self._text = ""

    
    def displayText(self):
        return self._text

class DummyHistory:
    def __init__(self):
        self._entries = []

    def append(self, s):
        self._entries.append(str(s))

    def setPlainText(self, s):
        self._entries = [str(s)]

    def toPlainText(self):
        return "\n".join(self._entries)

    def clear(self):
        self._entries = []

    @property
    def last(self):
        return self._entries[-1] if self._entries else ""

# Helper to attach dummy widgets under several possible attribute names
def attach_dummies(window, input_txt=""):
    input_names = ["input", "lineEdit", "inputLine", "leInput", "txtInput", "entry"]
    history_names = ["history", "textEdit", "txtHistory", "historyText", "txthistory"]
    dummy_in = DummyInput(input_txt)
    dummy_hist = DummyHistory()
    for name in input_names:
        setattr(window, name, dummy_in)
    for name in history_names:
        setattr(window, name, dummy_hist)
    return dummy_in, dummy_hist

# Tests for Calculator arithmetic and error conditions
@pytest.mark.parametrize(
    "a,b,expected",
    [
        (2, 3, 5),
        (-1, 1, 0),
        (0, 0, 0),
        (123456, 654321, 777777),
    ],
)
def test_Calculator_add_various(a, b, expected):
    
    # Arrange
    Calculator = getattr(calc_mod, "Calculator", None)
    assert Calculator is not None and inspect.isclass(Calculator)
    calc = Calculator()

    # Act
    result = calc.add(a, b)

    # Assert
    assert isinstance(result, (int, float))
    assert result == expected

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (5, 2, 3),
        (0, 5, -5),
        (-3, -2, -1),
    ],
)
def test_Calculator_subtract_various(a, b, expected):
    
    Calculator = getattr(calc_mod, "Calculator", None)
    assert Calculator is not None and inspect.isclass(Calculator)
    calc = Calculator()
    result = calc.subtract(a, b)
    assert isinstance(result, (int, float))
    assert result == expected

def test_Calculator_divide_by_zero_raises_CalculatorError():
    
    Calculator = getattr(calc_mod, "Calculator", None)
    CalculatorError = getattr(calc_mod, "CalculatorError", None)
    assert Calculator is not None and inspect.isclass(Calculator)
    assert CalculatorError is not None and inspect.isclass(CalculatorError)
    calc = Calculator()
    with pytest.raises(CalculatorError):
        calc.divide(1, 0)

# Tests for UI helper functions: clear_input and clear_history
def test_clear_input_clears_widget_function_or_method():
    
    
    func = getattr(app_mod, "clear_input", None)
    main_cls = getattr(app_mod, "MainWindow", None)

    dummy_window = types.SimpleNamespace()
    dummy_in, _ = attach_dummies(dummy_window, input_txt="some text")

    if callable(func):
        # module-level function that expects a window-like object
        func(dummy_window)
    elif main_cls is not None and hasattr(main_cls, "clear_input"):
        
        try:
            instance = main_cls()
        except Exception:
            # Fallback: create simple namespace and bind method
            instance = types.SimpleNamespace()
            method = getattr(main_cls, "clear_input")
            # bind as function to our instance
            bound = types.MethodType(method, instance)
            setattr(instance, "clear_input", bound)
        # attach dummies to instance
        attach_dummies(instance, input_txt="some text")
        instance.clear_input()
    else:
        pytest.skip("No clear_input function or MainWindow.clear_input found")

    # Assert that input is cleared
    assert dummy_in.text() == ""

def test_clear_history_clears_widget_function_or_method():
    
    func = getattr(app_mod, "clear_history", None)
    main_cls = getattr(app_mod, "MainWindow", None)

    dummy_window = types.SimpleNamespace()
    _, dummy_hist = attach_dummies(dummy_window)
    dummy_hist.setPlainText("existing history")

    if callable(func):
        func(dummy_window)
    elif main_cls is not None and hasattr(main_cls, "clear_history"):
        try:
            instance = main_cls()
        except Exception:
            instance = types.SimpleNamespace()
            method = getattr(main_cls, "clear_history")
            bound = types.MethodType(method, instance)
            setattr(instance, "clear_history", bound)
        attach_dummies(instance)
        instance.clear_history()
    else:
        pytest.skip("No clear_history function or MainWindow.clear_history found")

    # Assert history cleared
    assert dummy_hist.toPlainText() == ""

def test_calculate_uses_eval_and_appends_result(monkeypatch):
    
    
    calc_callable = getattr(app_mod, "calculate", None)
    main_cls = getattr(app_mod, "MainWindow", None)

    if not callable(calc_callable) and (main_cls is None or not hasattr(main_cls, "calculate")):
        pytest.skip("No calculate function or MainWindow.calculate method available")

    # Prepare dummy window and attach dummies
    dummy_window = types.SimpleNamespace()
    dummy_in, dummy_hist = attach_dummies(dummy_window, input_txt="2+3")

    # Monkeypatch builtins.eval to return a deterministic value for the expression "2+3"
    original_eval = builtins.eval

    def fake_eval(expr, *args, **kwargs):
        if isinstance(expr, str) and expr.strip() == "2+3":
            return 5
        return original_eval(expr, *args, **kwargs)

    monkeypatch.setattr(builtins, "eval", fake_eval)

    try:
        if callable(calc_callable):
            # module-level function expecting a window
            calc_callable(dummy_window)
        else:
            
            try:
                instance = main_cls()
            except Exception:
                instance = types.SimpleNamespace()
                method = getattr(main_cls, "calculate")
                bound = types.MethodType(method, instance)
                setattr(instance, "calculate", bound)
            attach_dummies(instance, input_txt="2+3")
            instance.calculate()
    finally:
        # restore eval just in case monkeypatch didn't (monkeypatch will restore automatically,
        # but ensure no leak if something goes wrong)
        monkeypatch.setattr(builtins, "eval", original_eval)

    
    assert isinstance(dummy_hist.last, str)
    assert "5" in dummy_hist.last.split() or dummy_hist.last.strip() == "5" or dummy_hist.last.endswith("5")
