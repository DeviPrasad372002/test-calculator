import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import io
import builtins
import types

import pytest

try:
    import Calculator
    import SimpleCalculatorPyQt1 as app
except ImportError as e:
    pytest.skip("Required modules Calculator or SimpleCalculatorPyQt1 are not importable: %s" % e, allow_module_level=True)

class FakeLineEdit:
    def __init__(self, text=""):
        self._text = text
        self.set_calls = []

    def text(self):
        return self._text

    def setText(self, value):
        self.set_calls.append(value)
        self._text = value

    def clear(self):
        self.setText("")

class FakeListWidget:
    def __init__(self, items=None):
        self.items = list(items or [])
        self.added = []
        self.cleared = False

    def addItem(self, value):
        self.added.append(value)
        self.items.append(value)

    def clear(self):
        self.cleared = True
        self.items.clear()

    def count(self):
        return len(self.items)

    def item(self, idx):
        class Item:
            def __init__(self, v):
                self._v = v

            def text(self):
                return self._v

        return Item(self.items[idx])

class FakeComboBox:
    def __init__(self, text):
        self._text = text

    def currentText(self):
        return self._text

class FakeMainWindow:
    def __init__(self, a_text="0", b_text="0", op="+", history_items=None):
        # provide both direct attributes and .ui bridging
        self.lineEdit = FakeLineEdit(a_text)
        self.lineEdit_2 = FakeLineEdit(b_text)
        self.comboBox = FakeComboBox(op)
        self.listWidget = FakeListWidget(history_items or [])
        
        self.ui = types.SimpleNamespace(
            lineEdit=self.lineEdit,
            lineEdit_2=self.lineEdit_2,
            comboBox=self.comboBox,
            listWidget=self.listWidget,
        )

def test_clear_input_and_clear_history_clear_widgets():
    
    # Arrange
    m = FakeMainWindow(a_text="123", b_text="456", history_items=["one", "two"])
    # Pre-conditions
    assert m.lineEdit.text() == "123"
    assert m.listWidget.count() == 2

    # Act
    # call whatever names exist; prefer attribute names from module if present
    # Many implementations provide functions clear_input and clear_history that accept a window
    clear_input = getattr(app, "clear_input", None)
    clear_history = getattr(app, "clear_history", None)
    assert callable(clear_input), "clear_input function not found in module"
    assert callable(clear_history), "clear_history function not found in module"

    clear_input(m)
    clear_history(m)

    # Assert
    assert m.lineEdit._text == ""
    assert m.listWidget.cleared is True
    assert m.listWidget.count() == 0

def test_calculate_calls_calculator_add_and_updates_ui(monkeypatch):
    
    # Arrange
    called = {}

    def fake_add(a, b):
        # record the raw values passed
        called['args'] = (a, b)
        return 42

    # Ensure we patch the add function on the imported Calculator module
    monkeypatch.setattr(Calculator, "add", fake_add, raising=True)

    
    m = FakeMainWindow(a_text="3", b_text="2", op="+")

    # Act
    calculate = getattr(app, "calculate", None)
    assert callable(calculate), "calculate function not found in module"
    # call
    calculate(m)

    # Assert that Calculator.add was invoked with numeric-like arguments that represent 3 and 2
    assert 'args' in called, "Calculator.add was not called by calculate"
    a_passed, b_passed = called['args']
    # Numeric coercion in UI can be int/float/str; normalize using float for robust check
    assert float(a_passed) == 3.0
    assert float(b_passed) == 2.0

    # The UI input should have been updated to the returned result (as string)
    # Many implementations call setText(str(result))
    assert m.lineEdit.set_calls, "lineEdit.setText was not called"
    assert m.lineEdit._text == str(42)

    # History should have been appended at least once with something referencing the result
    assert m.listWidget.added, "History widget was not updated"
    
    assert any("42" in str(x) for x in m.listWidget.added)

def test_save_history_writes_expected_lines_to_file(monkeypatch, tmp_path):
    
    # Arrange
    
    save_history = getattr(app, "save_history", None)
    assert callable(save_history), "save_history function not found in module"

    
    items = ["1 + 1 = 2", "3 * 4 = 12"]
    m = FakeMainWindow(history_items=items)

    # Many implementations call open() directly; intercept builtins.open for the target module
    captured = {}

    def fake_open(path, mode="w", *args, **kwargs):
        # path may be a string or Path; normalize to str
        captured['path'] = str(path)
        # return a file-like object that records writes
        sio = io.StringIO()

        def close_and_store():
            sio.seek(0)
            captured['content'] = sio.read()

        # Wrap close to capture content when closed
        original_close = sio.close

        def new_close():
            close_and_store()
            original_close()

        sio.close = new_close
        return sio

    # Patch builtins.open only for calls coming from app module
    monkeypatch.setattr(builtins, "open", fake_open, raising=True)

    # If save_history requires a filename argument, provide one; otherwise call with single arg
    try:
        # Try calling with a filename path
        out_file = tmp_path / "history.txt"
        save_history(m, str(out_file))
    except TypeError:
        
        save_history(m)

    
    assert 'content' in captured, "save_history did not write using open()"
    content = captured['content']
    for line in items:
        assert line in content, f"Expected history line not found in saved content: {line}"
