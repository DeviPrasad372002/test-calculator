import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import pytest
from pathlib import Path

try:
    from PyQt5 import QtWidgets
except ImportError:
    pytest.skip("PyQt5 is required for these tests", allow_module_level=True)

# Ensure a QApplication exists for widget construction
_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

try:
    import Calculator as CalculatorModule
    from Calculator import Calculator, CalculatorError
except ImportError:
    pytest.skip("Calculator module is required for these tests", allow_module_level=True)

try:
    import SimpleCalculatorPyQt1 as SimpleCalcModule
    from SimpleCalculatorPyQt1 import MainWindow
except ImportError:
    pytest.skip("SimpleCalculatorPyQt1 (MainWindow) is required for these tests", allow_module_level=True)

@pytest.mark.parametrize(
    "method_name,a,b,expected",
    [
        ("add", 1, 2, 3),
        ("subtract", 5, 2, 3),
        ("multiply", 3, 4, 12),
        ("divide", 8, 2, 4.0),
        ("divide", 7, 2.0, 3.5),
    ],
)
def test_calculator_arithmetic_methods_return_expected_values(method_name, a, b, expected):
    
    # Arrange
    calc = Calculator()

    # Act
    method = getattr(calc, method_name)
    result = method(a, b)

    # Assert
    assert isinstance(result, (int, float)), f"{method_name} should return a number"
    # Use exact equality for integers and floats produced by simple arithmetic here
    assert result == expected

def test_calculator_divide_by_zero_raises_calculator_error():
    
    # Arrange
    calc = Calculator()

    # Act / Assert
    with pytest.raises(CalculatorError) as excinfo:
        calc.divide(10, 0)
    # Ensure the exception is informative
    assert excinfo.value.args, "CalculatorError should contain message text"

def _find_input_widget(window):
    # prefer QLineEdit-like (has text and setText), else any object with these methods
    for obj in window.__dict__.values():
        if callable(getattr(obj, "setText", None)) and callable(getattr(obj, "text", None)):
            return obj
    return None

def _find_history_widget(window):
    
    for obj in window.__dict__.values():
        if callable(getattr(obj, "setPlainText", None)) and callable(getattr(obj, "toPlainText", None)):
            return ("qtext", obj)
        if callable(getattr(obj, "addItem", None)) and callable(getattr(obj, "count", None)):
            return ("qlist", obj)
    return (None, None)

def test_mainwindow_clear_input_and_clear_history_and_save_history(tmp_path, monkeypatch):
    
    # Arrange
    mw = MainWindow()  # instantiate the GUI window

    input_widget = _find_input_widget(mw)
    if input_widget is None:
        pytest.skip("No input widget with setText/text found on MainWindow instance")

    hist_type, history_widget = _find_history_widget(mw)
    if hist_type is None:
        pytest.skip("No history widget (QTextEdit or QListWidget-like) found on MainWindow instance")

    # Populate input and history
    input_widget.setText("42")
    if hist_type == "qtext":
        history_widget.setPlainText("previous: 1+1=2")
        expected_history_text = "previous: 1+1=2"
    else:
        # qlist
        history_widget.addItem("previous: 1+1=2")
        expected_history_text = "previous: 1+1=2"

    # Monkeypatch QFileDialog.getSaveFileName to return a deterministic path
    save_path = tmp_path / "history_out.txt"
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(save_path), None),
    )

    # Act - call save_history which should write current history to the chosen file
    assert hasattr(mw, "save_history"), "MainWindow must implement save_history()"
    mw.save_history()

    
    assert save_path.exists(), "save_history should create the file returned by QFileDialog.getSaveFileName"
    content = save_path.read_text(encoding="utf-8")
    assert expected_history_text in content

    # Act - clear history
    assert hasattr(mw, "clear_history"), "MainWindow must implement clear_history()"
    mw.clear_history()

    # Assert - history widget is cleared
    if hist_type == "qtext":
        assert history_widget.toPlainText() == ""
    else:
        assert history_widget.count() == 0

    # Act - clear input
    assert hasattr(mw, "clear_input"), "MainWindow must implement clear_input()"
    mw.clear_input()

    # Assert - input widget cleared
    assert input_widget.text() == ""

def test_mainwindow_calculate_uses_calculator_and_appends_history(monkeypatch):
    
    # Arrange
    mw = MainWindow()

    input_widget = _find_input_widget(mw)
    if input_widget is None:
        pytest.skip("No input widget with setText/text found on MainWindow instance")

    hist_type, history_widget = _find_history_widget(mw)
    if hist_type is None:
        pytest.skip("No history widget (QTextEdit or QListWidget-like) found on MainWindow instance")

    # Prepare a predictable calculation. We will monkeypatch Calculator methods to ensure deterministic outcome.
    
    monkeypatch.setattr(Calculator, "add", lambda self, x, y: x + y)
    monkeypatch.setattr(Calculator, "subtract", lambda self, x, y: x - y)
    monkeypatch.setattr(Calculator, "multiply", lambda self, x, y: x * y)
    monkeypatch.setattr(Calculator, "divide", lambda self, x, y: x / y)

    # Provide a simple expression that many simple calculators accept, e.g., "2+3"
    input_widget.setText("2+3")

    # Act
    assert hasattr(mw, "calculate"), "MainWindow must implement calculate()"
    mw.calculate()

    
    found = False
    if hist_type == "qtext":
        text = history_widget.toPlainText()
        found = "5" in text
    else:
        # iterate items
        for i in range(history_widget.count()):
            item = history_widget.item(i)
            if "5" in item.text():
                found = True
                break

    assert found, "After calculate(), the history widget should contain the result '5' of '2+3'"
