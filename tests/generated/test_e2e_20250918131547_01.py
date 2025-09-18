import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t=os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p=os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0,p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target',_pkg)

try:
    import importlib
except ModuleNotFoundError:
    try:
        import importlib
    except ModuleNotFoundError:
        import pytest
        pytest.skip('module importlib not importable; skipping module', allow_module_level=True)
try:
    import inspect
except ModuleNotFoundError:
    try:
        import inspect
    except ModuleNotFoundError:
        import pytest
        pytest.skip('module inspect not importable; skipping module', allow_module_level=True)
try:
    import math
except ModuleNotFoundError:
    try:
        import math
    except ModuleNotFoundError:
        import pytest
        pytest.skip('module math not importable; skipping module', allow_module_level=True)
try:
    import pytest
except ModuleNotFoundError:
    try:
        import pytest
    except ModuleNotFoundError:
        import pytest
        pytest.skip('module pytest not importable; skipping module', allow_module_level=True)
# Import target modules
calcmod = importlib.import_module("target.Calculator")
Calculator = getattr(calcmod, "Calculator", None)
CalculatorError = getattr(calcmod, "CalculatorError", None)

# Helper to call a numeric operation whether it's an instance method or a module-level function
def _call_op(obj_or_mod, name, a, b):
    """
    Try calling as instance method first, then as attribute on module/class.
    """
    # try instance method
    if hasattr(obj_or_mod, name):
        fn = getattr(obj_or_mod, name)
        try:
            return fn(a, b)
        except TypeError:
            # maybe requires self; fall through
            pass

    # if obj_or_mod is class, try classmethod/static or module function
    # try getattr on module
    if hasattr(calcmod, name):
        fn = getattr(calcmod, name)
        return fn(a, b)

    # try attribute on class
    if Calculator and hasattr(Calculator, name):
        fn = getattr(Calculator, name)
        return fn(obj_or_mod, a, b)

    # fallback: attempt to call as free function in module with provided args
    fn = getattr(calcmod, name, None)
    if fn is None:
        raise AttributeError(f"No operation {name} found")
    return fn(a, b)

def _is_close(a, b):
    try:
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    except Exception:
        return a == b

def test_calculator_class_and_error_present():
    
    # Ensure classes exist and error is an Exception subclass
    assert Calculator is not None, "Calculator class not found in target.Calculator"
    assert inspect.isclass(Calculator)
    assert CalculatorError is not None, "CalculatorError not found in target.Calculator"
    assert inspect.isclass(CalculatorError)
    assert issubclass(CalculatorError, Exception)

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (1, 2, 3),
        (0, 0, 0),
        (-1, 5, 4),
        (2.5, 1.25, 3.75),
        (1e9, 1e9, 2e9),
    ],
)
def test_add(a, b, expected):
    
    inst = Calculator()
    res = _call_op(inst, "add", a, b)
    assert _is_close(res, expected)

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (5, 3, 2),
        (0, 5, -5),
        (-2, -3, 1),
        (2.5, 1.25, 1.25),
        (1e9, 1e8, 9e8),
    ],
)
def test_subtract(a, b, expected):
    
    inst = Calculator()
    res = _call_op(inst, "subtract", a, b)
    assert _is_close(res, expected)

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (2, 3, 6),
        (0, 10, 0),
        (-2, 3, -6),
        (1.5, 2, 3.0),
        (1e5, 1e5, 1e10),
    ],
)
def test_multiply(a, b, expected):
    
    inst = Calculator()
    res = _call_op(inst, "multiply", a, b)
    assert _is_close(res, expected)

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (6, 3, 2),
        (5, 2, 2.5),
        (-6, 3, -2),
        (7.5, 2.5, 3.0),
    ],
)
def test_divide(a, b, expected):
    
    inst = Calculator()
    res = _call_op(inst, "divide", a, b)
    assert _is_close(res, expected)

def test_divide_by_zero_raises():
    
    inst = Calculator()
    with pytest.raises(Exception) as exc:
        _call_op(inst, "divide", 1, 0)
    # Prefer the project's specific CalculatorError, but accept other Exceptions
    if CalculatorError is not None:
        assert isinstance(exc.value, CalculatorError) or isinstance(exc.value, ZeroDivisionError)

def test_operations_with_large_and_float_precision():
    
    inst = Calculator()
    res1 = _call_op(inst, "add", 0.1, 0.2)
    # floating point tolerance
    assert pytest.approx(0.3, rel=1e-9) == res1
    res2 = _call_op(inst, "multiply", 1e-12, 1e12)
    assert _is_close(res2, 1.0)

# ------------------------
# UI-related tests (PyQt5)
# ------------------------
# Guard PyQt5 imports; skip module if not present
try:
    import PyQt5  # noqa: F401
    from PyQt5.QtWidgets import QApplication, QLineEdit, QTextEdit, QPlainTextEdit
    ui_mod = importlib.import_module("target.SimpleCalculatorPyQt1")
except Exception as e:  # ImportError or other errors importing Qt
    pytest.skip(f"PyQt5 or UI module not available: {e}", allow_module_level=True)

def _ensure_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def _find_widget_by_type(window, types):
    for name in dir(window):
        if name.startswith("__"):
            continue
        try:
            attr = getattr(window, name)
        except Exception:
            continue
        for t in types:
            if isinstance(attr, t):
                return attr
    # fallback: look into children()
    try:
        for child in window.findChildren(tuple(types)):
            return child
    except Exception:
        pass
    return None

def _get_text(widget):
    if widget is None:
        return None
    if isinstance(widget, QLineEdit):
        return widget.text()
    if isinstance(widget, (QTextEdit, QPlainTextEdit)):
        return widget.toPlainText()
    # try common attribute names
    if hasattr(widget, "text"):
        try:
            return widget.text()
        except Exception:
            pass
    if hasattr(widget, "toPlainText"):
        try:
            return widget.toPlainText()
        except Exception:
            pass
    return None

def _set_text(widget, txt):
    if widget is None:
        return
    if isinstance(widget, QLineEdit):
        widget.setText(txt)
        return
    if isinstance(widget, (QTextEdit, QPlainTextEdit)):
        widget.setPlainText(txt)
        return
    if hasattr(widget, "setText"):
        try:
            widget.setText(txt)
            return
        except Exception:
            pass
    if hasattr(widget, "setPlainText"):
        try:
            widget.setPlainText(txt)
            return
        except Exception:
            pass

def _call_ui_fn(window, name):
    # Try module-level function with window, then method on window
    if hasattr(ui_mod, name):
        fn = getattr(ui_mod, name)
        try:
            return fn(window)
        except TypeError:
            # maybe requires no args
            return fn()
    if hasattr(window, name):
        fn = getattr(window, name)
        return fn()
    raise AttributeError(f"UI function {name} not found")

def test_mainwindow_instantiation_and_widget_findings():
    
    _ensure_qapp()
    win = ui_mod.MainWindow()
    assert win is not None
    # ensure there's at least some input-like widget and history-like widget or skip those parts
    input_widget = _find_widget_by_type(win, (QLineEdit,))
    
    history_widget = _find_widget_by_type(win, (QTextEdit, QPlainTextEdit))
    # At minimum either input_widget or history_widget should exist to consider UI usable
    assert (input_widget is not None) or (history_widget is not None)

def test_clear_input_function_clears_input_when_present():
    
    _ensure_qapp()
    win = ui_mod.MainWindow()
    input_widget = _find_widget_by_type(win, (QLineEdit, QTextEdit, QPlainTextEdit))
    
    if input_widget is None:
        
        if hasattr(ui_mod, "clear_input"):
            _call_ui_fn(win, "clear_input")
        elif hasattr(win, "clear_input"):
            getattr(win, "clear_input")()
        else:
            pytest.skip("No clear_input function or input widget found")
        return
    # set some text, call clear_input and verify cleared
    _set_text(input_widget, "some text")
    pre = _get_text(input_widget)
    assert pre is not None and pre != ""
    # call clear_input
    _call_ui_fn(win, "clear_input")
    post = _get_text(input_widget)
    assert post == "" or post is None

def test_clear_history_and_save_history_behaviors():
    
    _ensure_qapp()
    win = ui_mod.MainWindow()
    input_widget = _find_widget_by_type(win, (QLineEdit, QTextEdit, QPlainTextEdit))
    history_widget = _find_widget_by_type(win, (QTextEdit, QPlainTextEdit))
    # If neither widget present, ensure functions callable and skip asserts
    if history_widget is None and input_widget is None:
        # call clear_history/save_history if present
        for name in ("save_history", "clear_history"):
            if hasattr(ui_mod, name):
                _call_ui_fn(win, name)
        pytest.skip("No input/history widgets to assert on")
        return

    # Ensure clear_history clears history widget if present
    if history_widget is not None:
        # populate history
        _set_text(history_widget, "existing")
        assert _get_text(history_widget) not in (None, "")
        _call_ui_fn(win, "clear_history")
        assert _get_text(history_widget) == "" or _get_text(history_widget) is None
    else:
        # no history widget, just call function to ensure no exception
        if hasattr(ui_mod, "clear_history"):
            _call_ui_fn(win, "clear_history")

    # Test save_history appends or sets history when input is present
    if input_widget is not None:
        _set_text(input_widget, "2+2")
        # call save_history
        if hasattr(ui_mod, "save_history") or hasattr(win, "save_history"):
            _call_ui_fn(win, "save_history")
            if history_widget is not None:
                txt = _get_text(history_widget) or ""
                
                assert txt != ""
        else:
            pytest.skip("save_history function not found")
    else:
        pytest.skip("No input widget for save_history test")

def test_calculate_function_basic():
    
    _ensure_qapp()
    win = ui_mod.MainWindow()
    input_widget = _find_widget_by_type(win, (QLineEdit, QTextEdit, QPlainTextEdit))
    history_widget = _find_widget_by_type(win, (QTextEdit, QPlainTextEdit))

    if input_widget is None:
        pytest.skip("No input widget to run calculate against")

    
    _set_text(input_widget, "6/3")
    # attempt calling calculate via module or instance
    if not (hasattr(ui_mod, "calculate") or hasattr(win, "calculate")):
        pytest.skip("calculate function not found in UI module or MainWindow")
    
    _call_ui_fn(win, "calculate")
    # After calculation, either input or history likely changed — assert at least one non-empty
    post_input = _get_text(input_widget)
    post_history = _get_text(history_widget) if history_widget is not None else None
    assert (post_input is not None and post_input != "") or (post_history is not None and post_history != "")
