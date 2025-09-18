import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import builtins
import types
import io
from types import SimpleNamespace

import pytest

# Guard third-party/module imports at module level
try:
    from target.Calculator import Calculator, CalculatorError
    import target.SimpleCalculatorPyQt1 as GUI
    # PyQt5 elements used by the GUI module
    import PyQt5.QtWidgets as QtWidgets
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)

def _ensure_attr_or_skip(obj, name):
    if not hasattr(obj, name):
        pytest.skip(f"Target does not expose expected attribute/method: {name}")

def _dummy_text_widget():
    class DummyText:
        def __init__(self):
            self.text = None

        def setPlainText(self, txt):
            self.text = txt

        def toPlainText(self):
            return "" if self.text is None else self.text

    return DummyText()

def _dummy_line_edit():
    class DummyLineEdit:
        def __init__(self):
            self._text = ""

        def setText(self, txt):
            self._text = txt

        def text(self):
            return self._text

    return DummyLineEdit()

def test_save_history_integration_writes_file(tmp_path, monkeypatch):
    
    # Arrange
    _ensure_attr_or_skip(GUI.MainWindow, "save_history")

    calc = Calculator()
    # Create history entries using Calculator to ensure cross-module behavior
    history = []
    history.append(f"1 + 2 = {calc.add(1, 2)}")
    history.append(f"5 * 3 = {calc.multiply(5, 3)}")
    history.append(f"10 - 4 = {calc.subtract(10, 4)}")
    # Deliberately produce a CalculatorError entry representation
    try:
        calc.divide(1, 0)
    except CalculatorError:
        history.append("1 / 0 = Error")

    fake_self = SimpleNamespace(history=history)

    # Prepare a target file inside tmp_path
    target_file = tmp_path / "history_out.txt"

    # Monkeypatch the file selection dialog to return our path.
    # PyQt5 QFileDialog.getSaveFileName typically returns (filename, filter)
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(target_file), ""))

    # Act
    GUI.MainWindow.save_history(fake_self)

    # Assert
    assert target_file.exists(), "save_history should create the chosen file path"
    content = target_file.read_text(encoding="utf-8")
    
    assert content.splitlines() == history

def test_clear_history_integration_clears_with_confirmation(monkeypatch):
    
    # Arrange
    _ensure_attr_or_skip(GUI.MainWindow, "clear_history")

    
    dummy_history_widget = _dummy_text_widget()
    fake_self = SimpleNamespace(
        history=["a", "b", "c"],
        history_text=dummy_history_widget
    )

    # Monkeypatch QMessageBox.question to simulate user clicking "Yes"
    # QMessageBox.Yes is an enum-like int; preserve original for return
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *a, **k: QtWidgets.QMessageBox.Yes)

    # Act
    GUI.MainWindow.clear_history(fake_self)

    # Assert - history list should be cleared and UI history text cleared
    assert fake_self.history == [], "clear_history should remove all entries from history list"
    
    assert getattr(fake_self, "history_text").text == ""

def test_clear_input_integration_resets_input_fields(monkeypatch):
    
    # Arrange
    _ensure_attr_or_skip(GUI.MainWindow, "clear_input")

    # Provide dummy line edits for typical input fields and ensure they start non-empty
    input1 = _dummy_line_edit()
    input2 = _dummy_line_edit()
    input1.setText("123")
    input2.setText("456")

    fake_self = SimpleNamespace(input1=input1, input2=input2)

    # Act
    GUI.MainWindow.clear_input(fake_self)

    # Assert both input widgets are cleared
    assert input1.text() == "", "clear_input should clear the first input field"
    assert input2.text() == "", "clear_input should clear the second input field"
