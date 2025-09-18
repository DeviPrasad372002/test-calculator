import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t=os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p=os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0,p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target',_pkg)

import sys
from pathlib import Path
import pytest

# Ensure target directory is importable
ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "target"
sys.path.insert(0, str(TARGET))

# Import the Calculator module (should be target/Calculator.py)
import importlib

calc_mod = importlib.import_module("Calculator")

# Helpers to access functions that may be module-level or instance methods
def _get_calc_instance():
    return calc_mod.Calculator()

def _get_callable(name):
    # Prefer module-level function if present
    if hasattr(calc_mod, name):
        return getattr(calc_mod, name)
    # fall back to instance bound method
    inst = _get_calc_instance()
    if hasattr(inst, name):
        return getattr(inst, name)
    raise AttributeError(f"No callable '{name}' found in module or Calculator instance")

# Basic Calculator / arithmetic tests (no PyQt needed)
@pytest.mark.parametrize(
    "fn_name,a,b,expected",
    [
        ("add", 2, 3, 5),
        ("add", 2.5, 1.25, 3.75),
        ("subtract", 5, 3, 2),
        ("subtract", 3.5, 1.2, 2.3),
        ("multiply", 4, 5, 20),
        ("multiply", 2.5, 4, 10.0),
        ("divide", 10, 2, 5),
        ("divide", 7.5, 2.5, 3.0),
    ],
)
def test_arithmetic_basic(fn_name, a, b, expected):
    
    fn = _get_callable(fn_name)
    res = fn(a, b)
    # allow float/int flexible equality
    assert pytest.approx(res, rel=1e-9, abs=1e-12) == expected

def test_divide_by_zero_raises():
    
    fn = _get_callable("divide")
    
    with pytest.raises(Exception) as excinfo:
        fn(1, 0)
    # If there is a specific CalculatorError class, it should be that or a subclass of Exception
    assert isinstance(excinfo.value, Exception)
    
    if hasattr(calc_mod, "CalculatorError"):
        assert isinstance(excinfo.value, (calc_mod.CalculatorError, ZeroDivisionError))

def test_non_numeric_inputs_raise_calculator_error_or_typeerror():
    
    
    fn = _get_callable("add")
    bad_vals = [("a", 1), (None, 2), ("x", "y")]
    for a, b in bad_vals:
        with pytest.raises(Exception):
            try:
                fn(a, b)
            except Exception as e:
                # Accept CalculatorError if present, otherwise common Python errors
                if hasattr(calc_mod, "CalculatorError") and isinstance(e, calc_mod.CalculatorError):
                    raise
                if isinstance(e, (TypeError, ValueError)):
                    raise
                
                raise

def test_calculator_class_and_error_presence():
    
    # Calculator class should be instantiable and have arithmetic methods
    assert hasattr(calc_mod, "Calculator")
    inst = calc_mod.Calculator()
    for name in ("add", "subtract", "multiply", "divide"):
        assert hasattr(inst, name)
        assert callable(getattr(inst, name))
    # CalculatorError should exist and be an Exception subclass if defined
    if hasattr(calc_mod, "CalculatorError"):
        err = calc_mod.CalculatorError("msg")
        assert isinstance(err, Exception)
        assert str(err) == "msg"

try:
    gui_mod = importlib.import_module("SimpleCalculatorPyQt1")
    HAVE_QT = True
except Exception:
    gui_mod = None
    HAVE_QT = False

# Guard import of PyQt5 widgets used for widget introspection/manipulation
if HAVE_QT:
    try:
        from PyQt5.QtWidgets import (
            QApplication,
            QTextEdit,
            QPlainTextEdit,
            QTextBrowser,
            QLineEdit,
            QFileDialog,
        )
    except Exception:
        HAVE_QT = False

pytestmark = pytest.mark.skipif(not HAVE_QT, reason="PyQt5 or GUI module not available")

def _find_widget_by_types(obj, types):
    # Search attributes of obj for first attribute that is instance of any types
    for attr in dir(obj):
        if attr.startswith("__"):
            continue
        try:
            val = getattr(obj, attr)
        except Exception:
            continue
        for t in types:
            try:
                if isinstance(val, t):
                    return val
            except Exception:
                
                pass
    return None

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_mainwindow_init_and_widget_presence(qapp):
    
    
    mw = gui_mod.MainWindow()
    assert hasattr(mw, "save_history")
    assert hasattr(mw, "clear_history")
    assert hasattr(mw, "clear_input")
    assert hasattr(mw, "calculate")
    assert callable(mw.save_history)
    assert callable(mw.clear_history)
    assert callable(mw.clear_input)
    assert callable(mw.calculate)

    # Find history and input widgets
    history_widget = _find_widget_by_types(
        mw, (QTextEdit, QPlainTextEdit, QTextBrowser)
    )
    input_widget = _find_widget_by_types(mw, (QLineEdit, QTextEdit, QPlainTextEdit))
    assert history_widget is not None, "Could not locate a history widget on MainWindow"
    assert input_widget is not None, "Could not locate an input widget on MainWindow"

def test_save_and_clear_history_file_io(tmp_path, qapp, monkeypatch):
    
    mw = gui_mod.MainWindow()
    history_widget = _find_widget_by_types(
        mw, (QTextEdit, QPlainTextEdit, QTextBrowser)
    )
    assert history_widget is not None

    # Set some history text
    test_text = "2 + 3 = 5\n4 * 5 = 20"
    # Use appropriate method depending on widget API
    if hasattr(history_widget, "setPlainText"):
        history_widget.setPlainText(test_text)
    elif hasattr(history_widget, "setText"):
        history_widget.setText(test_text)
    else:
        # Fallback: try to set attribute directly
        try:
            history_widget.text = test_text
        except Exception:
            pytest.skip("Unable to set history text on found widget type")

    out_file = tmp_path / "history_out.txt"

    # Monkeypatch QFileDialog.getSaveFileName to return our filename
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda parent=None, caption=None, directory=None, filter=None: (str(out_file), ""),
    )

    # Call save_history; handle different call signatures
    try:
        mw.save_history()
    except TypeError:
        # maybe expects a path argument
        mw.save_history(str(out_file))

    
    assert out_file.exists(), "save_history did not create the file"
    content = out_file.read_text()
    assert "2 + 3 = 5" in content and "4 * 5 = 20" in content

    # Now test clear_history clears the widget text
    # Put text back
    if hasattr(history_widget, "setPlainText"):
        history_widget.setPlainText("SOME TEXT")
    elif hasattr(history_widget, "setText"):
        history_widget.setText("SOME TEXT")

    try:
        mw.clear_history()
    except TypeError:
        mw.clear_history(None)

    # Verify cleared
    if hasattr(history_widget, "toPlainText"):
        assert history_widget.toPlainText() == ""
    elif hasattr(history_widget, "text"):
        # fallback: attribute or method
        val = history_widget.text() if callable(history_widget.text) else getattr(history_widget, "text", "")
        assert val == ""

def test_clear_input_and_calculate_changes_history(qapp, monkeypatch):
    
    mw = gui_mod.MainWindow()

    # Find widgets
    input_widget = _find_widget_by_types(mw, (QLineEdit, QTextEdit, QPlainTextEdit))
    history_widget = _find_widget_by_types(
        mw, (QTextEdit, QPlainTextEdit, QTextBrowser)
    )
    assert input_widget is not None
    assert history_widget is not None

    # Set input text to a simple expression
    expr = "2+3"
    if hasattr(input_widget, "setText"):
        input_widget.setText(expr)
    elif hasattr(input_widget, "setPlainText"):
        input_widget.setPlainText(expr)
    else:
        try:
            input_widget.text = expr
        except Exception:
            pytest.skip("Unable to set input text on input widget")

    # Record history before calculation
    if hasattr(history_widget, "toPlainText"):
        before = history_widget.toPlainText()
    elif hasattr(history_widget, "text"):
        before = history_widget.text() if callable(history_widget.text) else getattr(history_widget, "text", "")
    else:
        before = ""

    
    
    try:
        mw.calculator = calc_mod.Calculator()
    except Exception:
        # If attribute doesn't exist, create it anyway
        setattr(mw, "calculator", calc_mod.Calculator())

    
    # so handle both possibilities.
    try:
        mw.calculate()
    except Exception as e:
        # Accept CalculatorError or other exceptions that represent error handling
        if hasattr(calc_mod, "CalculatorError") and isinstance(e, calc_mod.CalculatorError):
            # expected error path for some implementations; test considered passed for error handling
            return
        
        raise

    # After successful calculate, history should have changed (append or replace)
    if hasattr(history_widget, "toPlainText"):
        after = history_widget.toPlainText()
    elif hasattr(history_widget, "text"):
        after = history_widget.text() if callable(history_widget.text) else getattr(history_widget, "text", "")
    else:
        after = ""

    assert after != before, "calculate did not change history widget content as expected"

    # Now test clear_input resets the input widget
    if hasattr(input_widget, "setText"):
        input_widget.setText("12345")
    elif hasattr(input_widget, "setPlainText"):
        input_widget.setPlainText("12345")

    try:
        mw.clear_input()
    except TypeError:
        mw.clear_input(None)

    if hasattr(input_widget, "text"):
        cur = input_widget.text() if callable(input_widget.text) else getattr(input_widget, "text", "")
        assert cur == ""
    elif hasattr(input_widget, "toPlainText"):
        assert input_widget.toPlainText() == ""
    else:
        # Fallback: attribute check
        assert getattr(input_widget, "text", "") in ("", None)
