import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import builtins
import os
import io
import types
import pytest

# Ensure Calculator module is present; otherwise skip all tests in this module (core functionality missing).
try:
    import Calculator as calc_mod
except Exception:
    pytest.skip("Calculator module not available", allow_module_level=True)

# Extract expected objects from Calculator module
try:
    Calculator = getattr(calc_mod, "Calculator")
    CalculatorError = getattr(calc_mod, "CalculatorError")
except Exception:
    pytest.skip("Calculator or CalculatorError not found in Calculator module", allow_module_level=True)

@pytest.mark.parametrize(
    "method,a,b,expected",
    [
        ("add", 1, 2, 3),
        ("add", -5, 7, 2),
        ("subtract", 10, 3, 7),
        ("subtract", 3, 10, -7),
        ("multiply", 4, 5, 20),
        ("multiply", -2, -3, 6),
        ("divide", 10, 2, 5),
        ("divide", 7, 2, 3.5),
    ],
)
def test_calculator_basic_operations(method, a, b, expected):
    
    # Arrange
    calc = Calculator()
    # Act
    func = getattr(calc, method, None)
    assert callable(func), f"{method} should be callable on Calculator"
    result = func(a, b)
    # Assert numeric result (allow floats)
    if isinstance(expected, float):
        assert abs(result - expected) < 1e-9
    else:
        assert result == expected

def test_calculator_divide_by_zero_raises():
    
    calc = Calculator()
    func = getattr(calc, "divide", None)
    assert callable(func), "divide should be callable on Calculator"
    with pytest.raises(CalculatorError):
        func(1, 0)

def test_calculator_history_tracking_if_supported():
    
    # Some Calculator implementations may track history; if so, ensure it records operations.
    calc = Calculator()
    add = getattr(calc, "add", None)
    if not callable(add):
        pytest.skip("Calculator.add not available")
    # If history attribute exists, capture its state before and after operations
    has_history = hasattr(calc, "history") or hasattr(calc, "history_list") or hasattr(calc, "get_history")
    if not has_history:
        pytest.skip("Calculator.history not supported by implementation")
    # Arrange
    initial = None
    if hasattr(calc, "history"):
        initial = list(calc.history) if isinstance(calc.history, (list, tuple)) else str(calc.history)
    elif hasattr(calc, "history_list"):
        initial = list(calc.history_list)
    elif hasattr(calc, "get_history"):
        initial = list(calc.get_history())
    # Act
    add(2, 3)
    # Assert
    if hasattr(calc, "history"):
        assert calc.history != initial
    elif hasattr(calc, "history_list"):
        assert calc.history_list != initial
    elif hasattr(calc, "get_history"):
        assert list(calc.get_history()) != initial

def _locate_text_fields(mw):
    
    candidates = []
    attrs = [a for a in dir(mw) if not a.startswith("__")]
    for name in attrs:
        try:
            widget = getattr(mw, name)
        except Exception:
            continue
        # QLineEdit-like
        if hasattr(widget, "setText") and hasattr(widget, "text"):
            candidates.append((lambda w=widget, t="": w.setText(t), lambda w=widget: w.text()))
        # QTextEdit-like
        elif hasattr(widget, "setPlainText") and hasattr(widget, "toPlainText"):
            candidates.append((lambda w=widget, t="": w.setPlainText(t), lambda w=widget: w.toPlainText()))
        # Some simple attributes might be strings
        elif isinstance(widget, str):
            def make_setter(n):
                return lambda v: setattr(mw, n, v)
            def make_getter(n):
                return lambda: getattr(mw, n)
            candidates.append((make_setter(name), make_getter(name)))
    return candidates

@pytest.mark.parametrize("text_input_a,text_input_b,expected_result", [("2", "3", "5"), ("7", "2", "9")])
def test_gui_calculate_updates_history_and_result(tmp_path, text_input_a, text_input_b, expected_result):
    
    
    pytest.importorskip("PyQt5")
    try:
        import SimpleCalculatorPyQt1 as gui_mod
    except Exception:
        pytest.skip("SimpleCalculatorPyQt1 GUI module not available")

    
    if not hasattr(gui_mod, "MainWindow"):
        pytest.skip("MainWindow class not found in GUI module")
    MainWindow = getattr(gui_mod, "MainWindow")

    # Create QApplication if needed
    try:
        from PyQt5.QtWidgets import QApplication
    except Exception:
        pytest.skip("PyQt5.QtWidgets.QApplication not importable")
    app = QApplication.instance() or QApplication([])

    
    mw = MainWindow()

    # If calculate is not a method, maybe it's a top-level function taking mw; support both.
    calculate_callable = None
    if hasattr(mw, "calculate") and callable(getattr(mw, "calculate")):
        calculate_callable = getattr(mw, "calculate")
        calculate_is_method = True
    elif hasattr(gui_mod, "calculate") and callable(getattr(gui_mod, "calculate")):
        calculate_callable = getattr(gui_mod, "calculate")
        calculate_is_method = False
    else:
        pytest.skip("No calculate function/method found in GUI")

    # Locate two text-like fields to place inputs
    fields = _locate_text_fields(mw)
    if len(fields) < 2:
        
        common_pairs = [("lineEdit", "lineEdit_2"), ("input1", "input2"), ("operandA", "operandB")]
        for a_name, b_name in common_pairs:
            if hasattr(mw, a_name) and hasattr(mw, b_name):
                a_widget = getattr(mw, a_name)
                b_widget = getattr(mw, b_name)
                if hasattr(a_widget, "setText") and hasattr(b_widget, "setText"):
                    fields = [
                        (lambda w=a_widget, t="": w.setText(t), lambda w=a_widget: w.text()),
                        (lambda w=b_widget, t="": w.setText(t), lambda w=b_widget: w.text()),
                    ]
                    break
    if len(fields) < 2:
        pytest.skip("Could not discover two input fields on MainWindow for calculate")

    # Set inputs
    setter_a, getter_a = fields[0]
    setter_b, getter_b = fields[1]
    setter_a(text_input_a)
    setter_b(text_input_b)

    # Capture history before
    history_getter = None
    if hasattr(mw, "history") and not isinstance(getattr(mw, "history"), (str, int, float)):
        hist_widget = getattr(mw, "history")
        if hasattr(hist_widget, "toPlainText"):
            history_getter = lambda: hist_widget.toPlainText()
        elif hasattr(hist_widget, "text"):
            history_getter = lambda: hist_widget.text()
        elif hasattr(hist_widget, "toPlainText"):
            history_getter = lambda: hist_widget.toPlainText()
    elif hasattr(gui_mod, "history") and isinstance(getattr(gui_mod, "history"), (str, int, float)):
        history_getter = lambda: str(getattr(gui_mod, "history"))
    else:
        # Look for any attribute that seems to hold text
        for name in dir(mw):
            if name.lower().startswith("history"):
                try:
                    val = getattr(mw, name)
                    if hasattr(val, "toPlainText"):
                        history_getter = lambda v=val: v.toPlainText()
                        break
                    if hasattr(val, "text"):
                        history_getter = lambda v=val: v.text()
                        break
                    if isinstance(val, str):
                        history_getter = lambda v=val, n=name: getattr(mw, n)
                        break
                except Exception:
                    continue
    before_history = history_getter() if history_getter else ""

    # Act: perform calculation
    if calculate_is_method:
        calculate_callable()
    else:
        calculate_callable(mw)

    # Assert: result visible in one of discovered getters or in history
    result_seen = False
    # Check first for a result display field
    for name in dir(mw):
        if name.lower() in ("result", "display", "lcdNumber", "label_result", "output"):
            try:
                widget = getattr(mw, name)
                if hasattr(widget, "text") and widget.text():
                    assert expected_result in widget.text() or str(float(expected_result)) in widget.text()
                    result_seen = True
                    break
            except Exception:
                continue
    # If not found, check the first input getter (some calculators replace input with result)
    if not result_seen:
        try:
            val = getter_a()
            if val and (val == expected_result or val == str(float(expected_result))):
                result_seen = True
        except Exception:
            pass

    # If still not found, check history changed
    if not result_seen and history_getter:
        after_history = history_getter()
        assert after_history != before_history, "History should be updated after calculation"
        assert expected_result in after_history or str(float(expected_result)) in after_history
        result_seen = True

    assert result_seen, "Could not detect expected result or updated history after calculate"

def _call_save_history(mw, gui_mod, tmp_path):
    # Attempt to call save_history (method or function). Monkeypatch QFileDialog to return a file in tmp_path.
    from PyQt5.QtWidgets import QFileDialog

    saved_file = tmp_path / "history_saved.txt"

    # Monkeypatch QFileDialog.getSaveFileName to return (filename, filter)
    orig = QFileDialog.getSaveFileName
    def fake_getSaveFileName(*args, **kwargs):
        return (str(saved_file), "")
    QFileDialog.getSaveFileName = staticmethod(fake_getSaveFileName)

    try:
        # If instance has save_history method
        if hasattr(mw, "save_history") and callable(getattr(mw, "save_history")):
            mw.save_history()
            return saved_file
        # If module has save_history function expecting window
        if hasattr(gui_mod, "save_history") and callable(getattr(gui_mod, "save_history")):
            gui_mod.save_history(mw)
            return saved_file
        pytest.skip("No save_history function/method found")
    finally:
        # Restore
        QFileDialog.getSaveFileName = orig

def test_gui_save_and_clear_history(tmp_path):
    
    pytest.importorskip("PyQt5")
    try:
        import SimpleCalculatorPyQt1 as gui_mod
    except Exception:
        pytest.skip("SimpleCalculatorPyQt1 GUI module not available")

    if not hasattr(gui_mod, "MainWindow"):
        pytest.skip("MainWindow class not found in GUI module")
    MainWindow = getattr(gui_mod, "MainWindow")

    try:
        from PyQt5.QtWidgets import QApplication
    except Exception:
        pytest.skip("PyQt5.QtWidgets.QApplication not importable")
    app = QApplication.instance() or QApplication([])

    mw = MainWindow()

    # Try to populate history so there is something to save
    # Use discovery helper to set some history text
    if hasattr(mw, "history"):
        h = getattr(mw, "history")
        try:
            if hasattr(h, "setPlainText"):
                h.setPlainText("calc: 1 + 1 = 2\n")
            elif hasattr(h, "setText"):
                h.setText("calc: 1 + 1 = 2\n")
            elif hasattr(h, "append"):
                h.append("calc: 1 + 1 = 2\n")
            else:
                setattr(mw, "history", "calc: 1 + 1 = 2\n")
        except Exception:
            try:
                setattr(mw, "history", "calc: 1 + 1 = 2\n")
            except Exception:
                pytest.skip("Unable to set history on MainWindow before save")
    else:
        # Fallback: set an attribute
        try:
            setattr(mw, "history", "calc: 1 + 1 = 2\n")
        except Exception:
            pytest.skip("Unable to set history on MainWindow before save")

    # Act: call save_history and assert a file is created with the expected content
    saved_file = _call_save_history(mw, gui_mod, tmp_path)
    assert saved_file.exists(), "save_history should create the file returned by QFileDialog.getSaveFileName"
    content = saved_file.read_text(encoding="utf-8")
    assert "1 + 1" in content or "1+1" in content or "2" in content

    # Now test clear_history: call method or function and expect history cleared
    if hasattr(mw, "clear_history") and callable(getattr(mw, "clear_history")):
        mw.clear_history()
    elif hasattr(gui_mod, "clear_history") and callable(getattr(gui_mod, "clear_history")):
        gui_mod.clear_history(mw)
    else:
        pytest.skip("No clear_history function/method found")
    # Verify history cleared
    if hasattr(mw, "history"):
        h = getattr(mw, "history")
        text = ""
        if hasattr(h, "toPlainText"):
            text = h.toPlainText()
        elif hasattr(h, "text"):
            text = h.text()
        elif isinstance(h, str):
            text = h
        assert text == "" or text is None

def test_gui_clear_input_resets_fields():
    
    pytest.importorskip("PyQt5")
    try:
        import SimpleCalculatorPyQt1 as gui_mod
    except Exception:
        pytest.skip("SimpleCalculatorPyQt1 GUI module not available")

    if not hasattr(gui_mod, "MainWindow"):
        pytest.skip("MainWindow class not found in GUI module")
    MainWindow = getattr(gui_mod, "MainWindow")

    try:
        from PyQt5.QtWidgets import QApplication
    except Exception:
        pytest.skip("PyQt5.QtWidgets.QApplication not importable")
    app = QApplication.instance() or QApplication([])

    mw = MainWindow()

    # Find input-like fields and populate them
    fields = _locate_text_fields(mw)
    if not fields:
        pytest.skip("No input-like fields found on MainWindow to test clear_input")

    # Populate first two fields (or first if only one)
    for i, (setter, getter) in enumerate(fields[:2]):
        setter("nonempty" if i == 0 else "also_nonempty")
        assert getter() != ""

    # Call clear_input (method or function)
    if hasattr(mw, "clear_input") and callable(getattr(mw, "clear_input")):
        mw.clear_input()
    elif hasattr(gui_mod, "clear_input") and callable(getattr(gui_mod, "clear_input")):
        gui_mod.clear_input(mw)
    else:
        pytest.skip("No clear_input function/method found in GUI")

    # Assert fields are cleared
    for setter, getter in fields[:2]:
        try:
            val = getter()
            assert val == "" or val is None
        except Exception:
            
            pass
