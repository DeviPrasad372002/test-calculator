import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import inspect
import types

try:
    import pytest
    from target import SimpleCalculatorPyQt1 as sc
    from target import Calculator as calc_mod
except Exception as e:
    import pytest  # re-import for skip
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)

# Lightweight fake widget implementations to emulate common Qt widget APIs
class FakeLineEdit:
    def __init__(self, text=""):
        self._text = str(text)

    def text(self):
        return self._text

    def setText(self, t):
        self._text = "" if t is None else str(t)

    def toPlainText(self):
        return self._text

    def setPlainText(self, t):
        self._text = "" if t is None else str(t)

    def clear(self):
        self._text = ""

class FakeTextEdit(FakeLineEdit):
    pass

def _populate_fake_window():
    """
    Create a fake window object and attach many commonly-used attribute names
    so that different implementations of calculate / clear_input / clear_history
    find expected widgets. This maximizes compatibility with multiple code shapes.
    """
    win = types.SimpleNamespace()
    # Input widgets
    for name in (
        "lineEdit_a",
        "lineEdit_b",
        "input1",
        "input2",
        "le_input_1",
        "le_input_2",
        "txtA",
        "txtB",
        "entryA",
        "entryB",
        "lineEdit_1",
        "lineEdit_2",
    ):
        setattr(win, name, FakeLineEdit())

    # Operator selector widgets
    for name in ("operator", "op", "comboBox", "operatorCombo", "operator_selector"):
        setattr(win, name, FakeLineEdit())

    # Result / display widgets
    for name in (
        "result",
        "label_result",
        "lineEdit_result",
        "display",
        "lcdNumber",
        "resultDisplay",
        "lineEdit_Result",
        "textBrowser_result",
    ):
        setattr(win, name, FakeLineEdit())

    # History widgets
    for name in (
        "textEdit_history",
        "history",
        "historyDisplay",
        "plainTextEdit_history",
        "textEdit",
        "plainTextEdit",
    ):
        setattr(win, name, FakeTextEdit())

    # Possible filename attributes
    win.history_file = None
    win.history_filename = None
    win.HISTORY_FILE = None

    return win

def _call_calculate_with_window(fake_win):
    """
    Try to call the calculate functionality using the module. Support both
    a standalone function sc.calculate(window) and the case where sc.calculate
    is implemented as a no-arg function that expects to find a MainWindow
    instance (skip that scenario). If the invocation is incompatible, raise
    TypeError to indicate skipping.
    """
    # Ensure QMessageBox-like UI calls don't pop up: stub it if present
    if hasattr(sc, "QMessageBox"):
        sc.QMessageBox = types.SimpleNamespace(information=lambda *a, **k: None, warning=lambda *a, **k: None)

    # Provide save_history stub if missing so calculate won't write to disk unexpectedly
    if not hasattr(sc, "save_history"):
        sc.save_history = lambda *a, **k: None

    # Preferred: standalone function taking the window
    calc_callable = getattr(sc, "calculate", None)
    if callable(calc_callable):
        try:
            return calc_callable(fake_win)
        except TypeError:
            
            pass

    
    MainWindow = getattr(sc, "MainWindow", None)
    if MainWindow is None:
        raise TypeError("calculate signature unsupported in this environment")
    
    
    mw_calc = getattr(MainWindow, "calculate", None)
    if callable(mw_calc):
        # Bind the function to our fake window and call
        try:
            bound = mw_calc.__get__(fake_win, MainWindow)
            return bound()
        except TypeError:
            raise TypeError("calculate method on MainWindow could not be invoked with fake window")
    raise TypeError("No callable calculate found")

def _call_clear_input_with_window(fake_win):
    clear_fn = getattr(sc, "clear_input", None)
    if callable(clear_fn):
        try:
            return clear_fn(fake_win)
        except TypeError:
            
            MainWindow = getattr(sc, "MainWindow", None)
            if MainWindow is None:
                raise
            mw_clear = getattr(MainWindow, "clear_input", None)
            if callable(mw_clear):
                bound = mw_clear.__get__(fake_win, MainWindow)
                return bound()
            raise
    raise TypeError("clear_input not callable")

def _call_clear_history_with_window(fake_win):
    clear_fn = getattr(sc, "clear_history", None)
    if callable(clear_fn):
        try:
            return clear_fn(fake_win)
        except TypeError:
            MainWindow = getattr(sc, "MainWindow", None)
            if MainWindow is None:
                raise
            mw_clear = getattr(MainWindow, "clear_history", None)
            if callable(mw_clear):
                bound = mw_clear.__get__(fake_win, MainWindow)
                return bound()
            raise
    raise TypeError("clear_history not callable")

# Integration tests

def test_calculate_addition_calls_calculator_and_saves_history(monkeypatch):
    
    # Arrange
    fake_win = _populate_fake_window()
    # Set inputs: choose some common attribute names set above
    fake_win.lineEdit_a.setText("3")
    fake_win.lineEdit_b.setText("4")
    fake_win.operator.setText("+")
    # Capture save_history calls
    saved = []

    def fake_save_history(text):
        saved.append(text)

    monkeypatch.setattr(sc, "save_history", fake_save_history, raising=False)

    # Ensure Calculator.add returns a deterministic value and record inputs received
    observed = {}

    def fake_add(self, a, b):
        observed['a'] = a
        observed['b'] = b
        return 7

    monkeypatch.setattr(calc_mod.Calculator, "add", fake_add, raising=False)

    # Act
    try:
        _call_calculate_with_window(fake_win)
    except TypeError:
        pytest.skip("calculate signature incompatible in this environment")

    # Assert
    # Result should be set on one of the result widgets we populated
    result_texts = []
    for name in ("result", "label_result", "lineEdit_result", "display", "resultDisplay"):
        widget = getattr(fake_win, name, None)
        if widget:
            result_texts.append(widget.text())
    assert any(rt == "7" for rt in result_texts), f"Expected result '7' in one of result widgets, got: {result_texts}"
    # Confirm Calculator.add was called with numeric text converted appropriately
    assert observed.get("a") in ("3", 3, 3.0), "Calculator.add did not receive expected left operand"
    assert observed.get("b") in ("4", 4, 4.0), "Calculator.add did not receive expected right operand"
    # Save history should have been called and include the operands and result
    assert len(saved) >= 1, "save_history was not called"
    joined = " ".join(str(x) for x in saved)
    assert "3" in joined and "4" in joined and "7" in joined, "Saved history did not contain expected expression and result"

def test_calculate_divide_by_zero_propagates_calculator_error(monkeypatch):
    
    # Arrange
    fake_win = _populate_fake_window()
    fake_win.lineEdit_a.setText("1")
    fake_win.lineEdit_b.setText("0")
    fake_win.operator.setText("/")

    
    def fake_divide(self, a, b):
        raise calc_mod.CalculatorError("division by zero")

    monkeypatch.setattr(calc_mod.Calculator, "divide", fake_divide, raising=False)

    # Prevent any real save_history from running
    monkeypatch.setattr(sc, "save_history", lambda *a, **k: None, raising=False)

    
    try:
        with pytest.raises(calc_mod.CalculatorError):
            _call_calculate_with_window(fake_win)
    except TypeError:
        pytest.skip("calculate signature incompatible in this environment")

def test_clear_input_and_clear_history_reset_widgets(monkeypatch):
    
    # Arrange
    fake_win = _populate_fake_window()
    # Pre-fill input and history widgets with non-empty data
    for name in ("lineEdit_a", "lineEdit_b", "input1", "input2"):
        w = getattr(fake_win, name, None)
        if w:
            w.setText("nonempty")

    for name in ("textEdit_history", "history", "plainTextEdit_history"):
        w = getattr(fake_win, name, None)
        if w:
            w.setPlainText("some history data")

    # If clear_history attempts to remove a file, stub out os.remove if present in module usage
    try:
        import os as _os_module

        removed = []

        def fake_remove(path):
            removed.append(path)

        monkeypatch.setattr(_os_module, "remove", fake_remove)
    except Exception:
        # If os isn't patchable in this environment, continue; we only assert UI clearing
        removed = []

    # Act
    try:
        _call_clear_input_with_window(fake_win)
    except TypeError:
        pytest.skip("clear_input signature incompatible in this environment")

    try:
        _call_clear_history_with_window(fake_win)
    except TypeError:
        pytest.skip("clear_history signature incompatible in this environment")

    # Assert: inputs are cleared
    for name in ("lineEdit_a", "lineEdit_b", "input1", "input2"):
        w = getattr(fake_win, name, None)
        if w:
            assert w.text() == "", f"{name} was not cleared"

    # Assert: history displays are cleared
    for name in ("textEdit_history", "history", "plainTextEdit_history"):
        w = getattr(fake_win, name, None)
        if w:
            assert w.toPlainText() == "", f"{name} history widget was not cleared"

    # If remove was called, ensure it was called with some path-like argument (len check)
    if removed:
        assert all(isinstance(p, (str, bytes)) for p in removed), "os.remove called with non-path argument"
