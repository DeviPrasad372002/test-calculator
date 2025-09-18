import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import inspect
import builtins
import io
import os
from unittest import mock

import pytest

# Guard third-party imports
try:
    from PyQt5 import QtWidgets, QtCore, QtGui
except ImportError:
    pytest.skip("PyQt5 is required for these integration tests", allow_module_level=True)

# Import target modules (try both top-level and 'target' package)
try:
    import target.Calculator as CalcMod
    import target.SimpleCalculatorPyQt1 as GuiMod
except Exception:
    try:
        import Calculator as CalcMod  # fallback
        import SimpleCalculatorPyQt1 as GuiMod
    except Exception:
        raise

Calculator = getattr(CalcMod, "Calculator")
CalculatorError = getattr(CalcMod, "CalculatorError")
MainWindowClass = getattr(GuiMod, "MainWindow")

def _instantiate_mainwindow(calculator_instance):
    """
    Instantiate MainWindow flexibly: if constructor accepts a calculator, pass it,
    otherwise construct with no args and attach calculator_instance if appropriate.
    """
    sig = inspect.signature(MainWindowClass)
    params = list(sig.parameters.values())
    try:
        if len(params) == 0:
            win = MainWindowClass()
        else:
            # try to pass calculator if param name looks relevant, otherwise pass nothing
            try:
                win = MainWindowClass(calculator_instance)
            except TypeError:
                win = MainWindowClass()
    except Exception:
        
        raise
    # If window has attribute to hold calculator, ensure it's our instance
    if hasattr(win, "calculator"):
        try:
            setattr(win, "calculator", calculator_instance)
        except Exception:
            pass
    return win

@pytest.fixture(autouse=True)
def ensure_qapplication():
    """
    Ensure a single QApplication exists for GUI integration tests.
    """
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield
    # Do not call app.quit() to avoid tearing down between tests; keep singleton

def _find_history_container(win):
    """
    Try to find a history container on the window.
    Return tuple(kind, obj) where kind is 'list' or 'qlistwidget' or 'attr' for plain attribute.
    """
    # Direct attribute named 'history'
    if hasattr(win, "history") and isinstance(getattr(win, "history"), list):
        return ("list", getattr(win, "history"))
    # Look for QListWidget-like
    for name in dir(win):
        if "history" in name.lower():
            obj = getattr(win, name)
            # QListWidget has count() and item()
            if hasattr(obj, "count") and hasattr(obj, "item"):
                return ("qlistwidget", obj)
            if isinstance(obj, list):
                return ("list", obj)
    
    for name in dir(win):
        if name.startswith("_"):
            continue
        obj = getattr(win, name)
        if isinstance(obj, list):
            
            return ("list", obj)
    return (None, None)

def _find_input_fields(win):
    """
    Find QLineEdit-like objects or attributes with 'input' in name.
    Return list of callables that when called return their current text.
    """
    inputs = []
    # QLineEdit has text() and setText()
    for name in dir(win):
        if "input" in name.lower() or "line" in name.lower() or "edit" in name.lower():
            obj = getattr(win, name)
            if hasattr(obj, "text") and callable(getattr(obj, "text")):
                inputs.append(obj)
            elif isinstance(obj, str):
                # attribute holding input text
                inputs.append(name)
    # fallback: look for attributes that are QLineEdit by checking methods
    if not inputs:
        for name in dir(win):
            obj = getattr(win, name)
            if hasattr(obj, "text") and hasattr(obj, "setText"):
                inputs.append(obj)
    return inputs

def _call_save_history(win, filepath, monkeypatch):
    """
    Call the save_history method on the window. If the method expects a filepath param, pass it.
    Otherwise, monkeypatch QFileDialog.getSaveFileName to return the filepath.
    """
    assert hasattr(win, "save_history"), "MainWindow lacks save_history method"
    save_fn = getattr(win, "save_history")
    sig = inspect.signature(save_fn)
    params = list(sig.parameters.values())
    # parameters include 'self' always; check if any others exist
    if len(params) > 1:
        # treat second param as filepath
        try:
            save_fn(str(filepath))
            return
        except TypeError:
            # fallback to using QFileDialog approach
            pass
    # monkeypatch QFileDialog.getSaveFileName
    # It often returns (str, selectedFilter) or just str; handle both by returning tuple
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(filepath), ""))
    save_fn()

def test_calculator_basic_operations_and_history_appended():
    
    # Arrange
    calc = Calculator()
    # Act / Assert for basic ops
    res1 = calc.add(3, 4)
    assert isinstance(res1, (int, float))
    assert res1 == 7
    res2 = calc.subtract(10, 2)
    assert res2 == 8
    res3 = calc.multiply(6, 7)
    assert res3 == 42
    res4 = calc.divide(20, 5)
    assert res4 == 4.0
    
    if hasattr(calc, "history"):
        assert isinstance(calc.history, list)
        # Expect at least four entries corresponding to operations
        assert len(calc.history) >= 4
        # Check last entries mention key operands/operators or results
        joined = " ".join(str(x) for x in calc.history[-4:])
        assert "3" in joined and "4" in joined and "42" in joined and "4.0" in joined

@pytest.mark.parametrize("a,b,expected", [(5, 2, 3), (2.5, 1.5, 1.0), (-1, -2, 1)])
def test_calculator_subtract_various(a, b, expected):
    
    # Arrange
    calc = Calculator()
    # Act
    result = calc.subtract(a, b)
    # Assert
    assert result == expected

def test_calculator_divide_by_zero_raises():
    
    # Arrange
    calc = Calculator()
    # Act / Assert
    with pytest.raises(CalculatorError):
        calc.divide(10, 0)

def test_mainwindow_save_history_writes_file_and_clear(monkeypatch, tmp_path):
    
    # Arrange: create calculator and perform operations to populate history
    calc = Calculator()
    calc.add(1, 2)
    calc.multiply(3, 4)
    # If Calculator exposed history, capture it for later assertion
    calc_history = getattr(calc, "history", None)
    
    win = _instantiate_mainwindow(calc)
    # Ensure window has save_history
    assert hasattr(win, "save_history")
    # Act: save history to file
    out_file = tmp_path / "history.txt"
    _call_save_history(win, out_file, monkeypatch)
    
    assert out_file.exists(), "save_history did not create the expected file"
    text = out_file.read_text(encoding="utf-8")
    assert len(text) > 0
    if calc_history:
        # Ensure at least one recorded history item appears in the file
        found_any = any(str(item) in text for item in calc_history)
        assert found_any, "Saved history did not contain calculator history entries"

def test_mainwindow_clear_history_and_clear_input(monkeypatch):
    
    # Arrange
    calc = Calculator()
    calc.add(7, 8)
    
    win = _instantiate_mainwindow(calc)
    
    inputs = _find_input_fields(win)
    # If inputs are QLineEdit-like, set text
    for inp in inputs:
        if hasattr(inp, "setText"):
            inp.setText("123")
        else:
            # attribute name case
            setattr(win, inp, "123")
    # Ensure there is some history visible via window (attempt to add from calculator.history)
    history_kind, history_obj = _find_history_container(win)
    # If the UI history is a QListWidget, try to populate it to verify clear works
    if history_kind == "qlistwidget":
        # Populate items
        history_obj.clear()
        for item_text in getattr(calc, "history", ["calc: 7+8"]):
            history_obj.addItem(str(item_text))
        assert history_obj.count() >= 1
    elif history_kind == "list":
        # populate list
        history_obj.clear()
        history_obj.extend(getattr(calc, "history", ["calc: 7+8"]))
        assert len(history_obj) >= 1
    else:
        
        if hasattr(win, "calculate"):
            try:
                win.calculate()
            except Exception:
                # ignore since UI may not be fully wired; proceed to call clear methods later
                pass

    # Act: call clear_history and clear_input if present
    if hasattr(win, "clear_history"):
        win.clear_history()
    if hasattr(win, "clear_input"):
        win.clear_input()

    # Assert: inputs cleared
    inputs_after = _find_input_fields(win)
    for inp in inputs_after:
        if hasattr(inp, "text"):
            assert inp.text() == "" or inp.text() == "0", "Input field not cleared"
        else:
            # attribute name
            val = getattr(win, inp, None)
            assert val == "" or val is None, "Input attribute not cleared"

    # Assert: history cleared
    history_kind_after, history_obj_after = _find_history_container(win)
    if history_kind_after == "qlistwidget":
        assert history_obj_after.count() == 0
    elif history_kind_after == "list":
        assert len(history_obj_after) == 0
    else:
        
        if hasattr(calc, "history"):
            assert isinstance(calc.history, list)  # sanity check only
