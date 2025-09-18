import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t=os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p=os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0,p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target',_pkg)

import inspect
import os
import builtins
import pytest

# Import the calculator module under test
import target.Calculator as CalcMod
from target.Calculator import Calculator, CalculatorError

try:
    from PyQt5 import QtWidgets, QtCore, QtGui
except ImportError:
    QtWidgets = None

if QtWidgets is None:
    pytest.skip("PyQt5 not available; skipping MainWindow GUI tests", allow_module_level=True)

from target.SimpleCalculatorPyQt1 import MainWindow

# Helper to find a numeric state attribute on Calculator instances
def find_numeric_state(calc):
    for name in ("value", "total", "result", "current", "display", "memory"):
        if hasattr(calc, name):
            val = getattr(calc, name)
            if isinstance(val, (int, float)):
                return name, val
    return None, None

# Helper to attempt calling a bound method with different arities
def try_call_method(method, *args):
    sig = inspect.signature(method)
    param_count = len(sig.parameters)
    # param_count is the number of parameters expected (for bound methods)
    try:
        if param_count >= len(args):
            return method(*args[:param_count])
        else:
            # If less parameters than provided, try with only as many as expected
            return method(*args[:param_count])
    except TypeError:
        # fallback: try calling with no args
        return method()

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (7, 3, 10),    # add
        (7.5, 2.5, 10.0),
        (-2, 5, 3),
    ],
)
def test_add_two_arg_behaviour(a, b, expected):
    
    calc = Calculator()
    add_m = getattr(calc, "add", None)
    assert add_m is not None, "Calculator.add missing"
    sig = inspect.signature(add_m)
    if len(sig.parameters) >= 2:
        res = add_m(a, b)
        # If returns None, try to inspect internal numeric state
        if res is None:
            name, val = find_numeric_state(calc)
            assert name is not None, "add did not return value and no numeric state found"
            assert pytest.approx(val, rel=1e-9) == expected
        else:
            assert pytest.approx(res, rel=1e-9) == expected
    else:
        pytest.skip("add does not support two-argument calling convention; skipping two-arg test")

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (7, 3, 4),
        (2.5, 1.5, 1.0),
        (-2, -3, 1),
    ],
)
def test_subtract_two_arg_behaviour(a, b, expected):
    
    calc = Calculator()
    sub_m = getattr(calc, "subtract", None)
    assert sub_m is not None, "Calculator.subtract missing"
    sig = inspect.signature(sub_m)
    if len(sig.parameters) >= 2:
        res = sub_m(a, b)
        if res is None:
            name, val = find_numeric_state(calc)
            assert name is not None, "subtract did not return value and no numeric state found"
            assert pytest.approx(val, rel=1e-9) == expected
        else:
            assert pytest.approx(res, rel=1e-9) == expected
    else:
        pytest.skip("subtract does not support two-argument calling convention; skipping two-arg test")

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (6, 7, 42),
        (2.5, 4, 10.0),
        (-3, 5, -15),
    ],
)
def test_multiply_two_arg_behaviour(a, b, expected):
    
    calc = Calculator()
    mul_m = getattr(calc, "multiply", None)
    assert mul_m is not None, "Calculator.multiply missing"
    sig = inspect.signature(mul_m)
    if len(sig.parameters) >= 2:
        res = mul_m(a, b)
        if res is None:
            name, val = find_numeric_state(calc)
            assert name is not None, "multiply did not return value and no numeric state found"
            assert pytest.approx(val, rel=1e-9) == expected
        else:
            assert pytest.approx(res, rel=1e-9) == expected
    else:
        pytest.skip("multiply does not support two-argument calling convention; skipping two-arg test")

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (10, 2, 5),
        (7.5, 2.5, 3.0),
        (-8, 4, -2),
    ],
)
def test_divide_two_arg_behaviour(a, b, expected):
    
    calc = Calculator()
    div_m = getattr(calc, "divide", None)
    assert div_m is not None, "Calculator.divide missing"
    sig = inspect.signature(div_m)
    if len(sig.parameters) >= 2:
        res = div_m(a, b)
        if res is None:
            name, val = find_numeric_state(calc)
            assert name is not None, "divide did not return value and no numeric state found"
            assert pytest.approx(val, rel=1e-9) == expected
        else:
            assert pytest.approx(res, rel=1e-9) == expected
    else:
        pytest.skip("divide does not support two-argument calling convention; skipping two-arg test")

def test_divide_by_zero_raises_calculator_error_two_arg():
    
    calc = Calculator()
    div_m = getattr(calc, "divide", None)
    assert div_m is not None, "Calculator.divide missing"
    sig = inspect.signature(div_m)
    if len(sig.parameters) >= 2:
        with pytest.raises(CalculatorError):
            div_m(5, 0)
    else:
        pytest.skip("divide does not support two-argument calling convention; skipping divide-by-zero test")

def test_divide_by_zero_raises_calculator_error_single_arg_if_supported():
    
    calc = Calculator()
    div_m = getattr(calc, "divide", None)
    assert div_m is not None, "Calculator.divide missing"
    sig = inspect.signature(div_m)
    # handle the single-argument mode where divide(x) divides the internal state by x
    if len(sig.parameters) == 1:
        # set an identifiable numeric internal state if possible
        name, val = find_numeric_state(calc)
        if name is not None:
            # set a nonzero state so dividing by zero is still meaningful
            try:
                setattr(calc, name, 5)
            except Exception:
                pytest.skip("Cannot set internal state; skipping single-arg divide-by-zero test")
            with pytest.raises(CalculatorError):
                div_m(0)
        else:
            pytest.skip("No numeric internal state to test single-arg divide-by-zero")
    else:
        pytest.skip("divide does not support single-argument calling convention; skipping single-arg test")

def test_chained_single_arg_operations_if_initial_zero():
    
    calc = Calculator()
    # We will only run this test if methods support single-arg calling convention and initial numeric state is zero.
    add_m = getattr(calc, "add", None)
    mul_m = getattr(calc, "multiply", None)
    sub_m = getattr(calc, "subtract", None)
    div_m = getattr(calc, "divide", None)
    if not all([add_m, mul_m, sub_m, div_m]):
        pytest.skip("Calculator missing one of add/multiply/subtract/divide; skipping chained single-arg test")
    sigs = [inspect.signature(m) for m in (add_m, mul_m, sub_m, div_m)]
    if not all(len(s.parameters) == 1 for s in sigs):
        pytest.skip("Not all operations support single-argument calling convention; skipping chained single-arg test")
    name, val = find_numeric_state(calc)
    if name is None:
        pytest.skip("No numeric internal state to test chained single-arg operations")
    if val != 0 and val != 0.0:
        pytest.skip(f"Initial internal state is not zero (found {val}); skipping chained single-arg test")
    # Perform (0 + 5) * 2 - 3 = 7, then / 2 = 3.5
    add_m(5)
    mul_m(2)
    sub_m(3)
    res = div_m(2)
    if res is None:
        # read back internal state
        name2, val2 = find_numeric_state(calc)
        assert name2 is not None
        assert pytest.approx(val2, rel=1e-9) == 3.5
    else:
        assert pytest.approx(res, rel=1e-9) == 3.5

@pytest.fixture(autouse=True)
def ensure_qapplication(monkeypatch):
    """Ensure there is a running QApplication for widget tests."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield
    # Do not call app.quit() to avoid tearing down global state mid-test run

def find_line_edits(widget):
    return widget.findChildren(QtWidgets.QLineEdit)

def find_text_edits(widget):
    return widget.findChildren(QtWidgets.QTextEdit)

def find_list_widgets(widget):
    return widget.findChildren(QtWidgets.QListWidget)

def get_history_texts(widget):
    # Try QTextEdit then QListWidget for textual history
    te = find_text_edits(widget)
    if te:
        return [t.toPlainText() for t in te]
    lw = find_list_widgets(widget)
    if lw:
        # flatten items
        texts = []
        for l in lw:
            for i in range(l.count()):
                texts.append(l.item(i).text())
        return texts
    return []

def set_history_content(widget, content):
    te = find_text_edits(widget)
    if te:
        for t in te:
            t.setPlainText(content)
        return True
    lw = find_list_widgets(widget)
    if lw:
        for l in lw:
            l.clear()
            for line in content.splitlines():
                l.addItem(line)
        return True
    return False

def test_clear_input_clears_lineedits():
    
    win = MainWindow()
    line_edits = find_line_edits(win)
    if not line_edits:
        pytest.skip("No QLineEdit widgets found in MainWindow; skipping clear_input test")
    # populate them
    for idx, le in enumerate(line_edits):
        le.setText(f"val{idx}")
    # call clear_input
    ci = getattr(win, "clear_input", None)
    assert ci is not None, "MainWindow.clear_input missing"
    ci()
    # assert cleared
    for le in line_edits:
        assert le.text() == ""

def test_clear_history_clears_history_widgets():
    
    win = MainWindow()
    # ensure there is some history widget
    if not (find_text_edits(win) or find_list_widgets(win)):
        pytest.skip("No history widgets (QTextEdit/QListWidget) found; skipping clear_history test")
    # set some content
    set_history_content(win, "line1\nline2")
    ch = getattr(win, "clear_history", None)
    assert ch is not None, "MainWindow.clear_history missing"
    ch()
    # verify cleared
    texts = get_history_texts(win)
    # For QTextEdit expect empty strings; for QListWidget expect no items
    if find_text_edits(win):
        for t in texts:
            assert t == ""
    else:
        assert texts == []

def test_save_history_writes_file(tmp_path, monkeypatch):
    
    win = MainWindow()
    # only run if there is history content
    if not (find_text_edits(win) or find_list_widgets(win)):
        pytest.skip("No history widgets found; skipping save_history test")
    test_content = "h1\nh2\nh3"
    assert set_history_content(win, test_content)
    # Monkeypatch QFileDialog.getSaveFileName to return a deterministic file path
    target_path = tmp_path / "history_out.txt"
    def fake_get_save_file_name(*args, **kwargs):
        # PyQt returns a tuple (filename, filter) in many patterns
        return (str(target_path), '')
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", staticmethod(fake_get_save_file_name))
    save = getattr(win, "save_history", None)
    assert save is not None, "MainWindow.save_history missing"
    
    save()
    
    assert target_path.exists(), "save_history did not create the expected file"
    data = target_path.read_text(encoding="utf-8")
    # Assert that at least one of the lines appears in the file
    assert "h1" in data or "h2" in data or "h3" in data

def test_calculate_callable_and_no_crash(monkeypatch):
    
    win = MainWindow()
    calc_fn = getattr(win, "calculate", None)
    if calc_fn is None:
        pytest.skip("MainWindow.calculate missing; skipping calculate test")
    # Try to set a couple of input fields to valid numeric values if present
    line_edits = find_line_edits(win)
    if line_edits:
        # fill first two line edits with numeric values if there are at least one
        for i, le in enumerate(line_edits[:2]):
            le.setText(str(2 + i))
    # Protect any file dialogs or message boxes invoked during calculate by patching them to be no-op
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", staticmethod(lambda *a, **k: None), raising=False)
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", staticmethod(lambda *a, **k: None), raising=False)
    
    try:
        calc_fn()
    except Exception as e:
        pytest.fail(f"MainWindow.calculate raised an exception: {e}")
