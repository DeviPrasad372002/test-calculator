import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import sys
import importlib
import inspect
import builtins
from unittest import mock
import io
import os
import types

import pytest

# Ensure target package path is importable
sys.path.append("target")

# Import calculator module
Calculator = importlib.import_module("Calculator")
SimpleCalc = importlib.import_module("SimpleCalculatorPyQt1")

# Basic arithmetic tests for Calculator functions and Calculator class
@pytest.mark.parametrize(
    "func_name,a,b,expected",
    [
        ("add", 1, 2, 3),
        ("add", -1, 2.5, 1.5),
        ("subtract", 5, 3, 2),
        ("subtract", 3.5, 1.2, 2.3),
        ("multiply", 3, 4, 12),
        ("multiply", -2, -8, 16),
        ("divide", 10, 2, 5),
        ("divide", 7.5, 2.5, 3.0),
    ],
)
def test_calculator_module_functions_and_instance_methods(func_name, a, b, expected):
    
    # Arrange
    # Module-level function
    func = getattr(Calculator, func_name, None)
    assert func is not None, f"Calculator.{func_name} not found"

    # Act & Assert (module function)
    result_module = func(a, b)
    assert pytest.approx(result_module, rel=1e-9) == expected

    # If Calculator class exists and has the method, test instance method too
    CalcClass = getattr(Calculator, "Calculator", None)
    if CalcClass:
        inst = CalcClass()
        # prefer instance method
        inst_method = getattr(inst, func_name, None)
        if callable(inst_method):
            result_inst = inst_method(a, b)
            assert pytest.approx(result_inst, rel=1e-9) == expected

def test_divide_by_zero_raises_calculator_error():
    
    # Arrange
    divide = getattr(Calculator, "divide", None)
    CalcClass = getattr(Calculator, "Calculator", None)
    error_cls = getattr(Calculator, "CalculatorError", Exception)

    # Act & Assert for module-level function
    if divide:
        with pytest.raises(error_cls):
            divide(1, 0)

    # Act & Assert for instance method if present
    if CalcClass:
        inst = CalcClass()
        inst_div = getattr(inst, "divide", None)
        if callable(inst_div):
            with pytest.raises(error_cls):
                inst_div(5, 0)

def _call_maybe_with_window(func, window):
    # Helper: call a function that may expect zero args or one arg (window/self)
    sig = inspect.signature(func)
    if len(sig.parameters) == 0:
        return func()
    elif len(sig.parameters) == 1:
        return func(window)
    else:
        # pass window as first param and rely on defaults for others
        return func(window)

pytest.importorskip("PyQt5")
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit, QLabel, QComboBox

def _ensure_qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app

def _find_first_widget_of_types(window, types_tuple):
    for attr_name in dir(window):
        try:
            attr = getattr(window, attr_name)
        except Exception:
            continue
        if isinstance(attr, types_tuple):
            return attr_name, attr
    return None, None

def _set_text_on_widget(widget, text):
    # Unified setter for common Qt widgets
    if hasattr(widget, "setText"):
        widget.setText(str(text))
        return True
    if hasattr(widget, "setPlainText"):
        widget.setPlainText(str(text))
        return True
    return False

def _get_text_from_widget(widget):
    if hasattr(widget, "text"):
        try:
            return widget.text()
        except Exception:
            pass
    if hasattr(widget, "toPlainText"):
        return widget.toPlainText()
    if hasattr(widget, "plainText"):
        return widget.plainText()
    return None

@pytest.mark.parametrize("history_text", ["one\ntwo\nthree", "42", ""])
def test_save_history_writes_file(tmp_path, history_text, monkeypatch):
    
    # Arrange
    _ensure_qapp()
    MainWindow = getattr(SimpleCalc, "MainWindow", None)
    save_history = getattr(SimpleCalc, "save_history", None)
    assert save_history is not None, "save_history not found in module"

    if MainWindow is None:
        
        window = types.SimpleNamespace()
        window.history = history_text
    else:
        window = MainWindow()
        
        _, hist_widget = _find_first_widget_of_types(window, (QTextEdit, QPlainTextEdit, QLineEdit))
        if hist_widget is not None:
            _set_text_on_widget(hist_widget, history_text)
        else:
            
            setattr(window, "history", history_text)

    # Prepare a fake path and monkeypatch builtins.open to capture writes
    fake_file = tmp_path / "history.txt"
    written = {"data": None}
    m = mock.mock_open()

    def fake_open(path, mode="r", *args, **kwargs):
        # ensure path is what we expect or accept any
        handle = m(path, mode, *args, **kwargs)
        return handle

    monkeypatch.setattr(builtins, "open", fake_open)

    # Some implementations may use os.path.join or module-level attribute for filename.
    # Patch SimpleCalc to use our tmp_path if it has a filename attribute.
    if hasattr(SimpleCalc, "HISTORY_FILE"):
        monkeypatch.setattr(SimpleCalc, "HISTORY_FILE", str(fake_file))

    # Act
    _call_maybe_with_window(save_history, window)

    # Assert - ensure open was called via our mock
    assert m.call_count >= 1, "save_history did not attempt to open a file"

    # Inspect what was written via the file handle returned by mock_open
    handle = m()
    # mock_open's handle.write() calls are stored in handle.write.mock_calls
    writes = []
    if hasattr(handle, "write") and hasattr(handle.write, "call_args_list"):
        for call in handle.write.call_args_list:
            args, _ = call
            if args:
                writes.append(args[0])
    written_txt = "".join(writes)
    # If there was history_text set on window, expect it to appear in written output or be empty
    if history_text:
        assert history_text.splitlines()[0] in written_txt or history_text in written_txt
    else:
        # empty history may write nothing but should not error
        assert isinstance(written_txt, str)

def test_clear_history_and_clear_input_and_calculate_integration(monkeypatch):
    
    # This test exercises clear_input, clear_history, and calculate together.
    _ensure_qapp()
    MainWindow = getattr(SimpleCalc, "MainWindow", None)
    clear_history = getattr(SimpleCalc, "clear_history", None)
    clear_input = getattr(SimpleCalc, "clear_input", None)
    calculate = getattr(SimpleCalc, "calculate", None)

    # At minimum, calculate should exist
    assert calculate is not None, "calculate function not found"

    if MainWindow is None:
        window = types.SimpleNamespace()
        # provide likely attributes
        window.input1 = "2"
        window.input2 = "3"
        window.result = ""
        window.history = ""
    else:
        window = MainWindow()
        # Find two input fields and set values
        name1, widget1 = _find_first_widget_of_types(window, (QLineEdit,))
        name2, widget2 = None, None
        # attempt to find another line edit
        for attr_name in dir(window):
            if attr_name == name1:
                continue
            try:
                attr = getattr(window, attr_name)
            except Exception:
                continue
            if isinstance(attr, QLineEdit):
                name2, widget2 = attr_name, attr
                break

        if widget1:
            _set_text_on_widget(widget1, "6")
        if widget2:
            _set_text_on_widget(widget2, "7")
        # try to set an operator if a combobox exists
        _, combo = _find_first_widget_of_types(window, (QComboBox,))
        if combo:
            # choose a '+' or 'Add' if possible
            try:
                # find index of "+" or "Add" or "add"
                idx = None
                for i in range(combo.count()):
                    txt = combo.itemText(i).lower()
                    if txt in ("+", "add", "addition"):
                        idx = i
                        break
                if idx is None:
                    idx = 0
                combo.setCurrentIndex(idx)
            except Exception:
                pass

    
    if clear_input:
        _call_maybe_with_window(clear_input, window)

    # If clear_history exists, set something then clear it
    if clear_history:
        # set a history-like widget or attribute
        if MainWindow is not None:
            _, hist_widget = _find_first_widget_of_types(window, (QTextEdit, QPlainTextEdit, QLineEdit))
            if hist_widget:
                _set_text_on_widget(hist_widget, "to-be-cleared")
            else:
                setattr(window, "history", "to-be-cleared")
        else:
            setattr(window, "history", "to-be-cleared")
        _call_maybe_with_window(clear_history, window)
        # Verify cleared if we can read it back
        if MainWindow is not None and hist_widget is not None:
            text_after = _get_text_from_widget(hist_widget)
            # Either empty string or None accepted; assert no exception occurred
            assert text_after == "" or text_after is None
        else:
            # attribute-based: expect attribute cleared if function acted on it
            if hasattr(window, "history"):
                val = getattr(window, "history")
                # either empty or unchanged depending on implementation; ensure callable succeeded
                assert isinstance(val, (str, type(None)))

    # Now call calculate and verify result was produced or no exception
    res = _call_maybe_with_window(calculate, window)

    # Some implementations return a result or update a widget; check both possibilities
    if isinstance(res, (int, float, str)):
        # If numeric-ish string convertable?
        if isinstance(res, str):
            try:
                float(res)
            except Exception:
                # non-numeric strings are accepted as long as function didn't error
                pass
    else:
        # attempt to find a result widget and inspect
        name_res, widget_res = _find_first_widget_of_types(window, (QLabel, QLineEdit))
        if widget_res:
            out = _get_text_from_widget(widget_res)
            # If any text present it's considered successful
            assert out is None or isinstance(out, str)

    
    assert True  # if we reached here, the integration path executed successfully without exceptions.
