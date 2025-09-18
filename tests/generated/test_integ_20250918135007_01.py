import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import builtins
import inspect
import io
import os

try:
    import pytest
    from target import Calculator
    from target import SimpleCalculatorPyQt1
    # PyQt can be optional in the project; ensure it's importable for GUI-related integration tests
    from PyQt5 import QtWidgets
except ImportError as e:
    import pytest
    pytest.skip(f"Skipping integration tests due to import error: {e}", allow_module_level=True)

class _FakeFile:
    def __init__(self):
        self.buffer = io.StringIO()
        self.closed = False

    def write(self, data):
        return self.buffer.write(data)

    def writelines(self, lines):
        return self.buffer.writelines(lines)

    def read(self):
        return self.buffer.getvalue()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True

def _make_dummy_window_for_save(src_text, tmp_history_lines):
    """
    Create a lightweight dummy object compatible with possible save_history implementations.
    It will try to satisfy either .history (list of strings) or .calculator.history (list).
    """
    class Dummy:
        pass

    d = Dummy()
    # Provide common shapes
    d.history = list(tmp_history_lines)
    # Provide calculator member that itself has history attribute
    class CalcProxy:
        def __init__(self, history):
            self.history = list(history)
    d.calculator = CalcProxy(tmp_history_lines)
    # Sometimes save_history might inspect UI elements like self.lineEdit or similar; provide safe defaults
    d.lineEdit = type("LE", (), {"text": lambda self: ""})()
    return d

def _find_save_func():
    # Try module-level save_history first
    save_func = getattr(SimpleCalculatorPyQt1, "save_history", None)
    if save_func is not None:
        return save_func
    
    MainWindow = getattr(SimpleCalculatorPyQt1, "MainWindow", None)
    if MainWindow is not None:
        return getattr(MainWindow, "save_history", None)
    return None

def _module_references_calculator_class():
    # Check whether SimpleCalculatorPyQt1 references the Calculator class object from Calculator module
    target_class = getattr(Calculator, "Calculator", None)
    if target_class is None:
        return False
    for val in vars(SimpleCalculatorPyQt1).values():
        if val is target_class:
            return True
    return False

def _get_add_and_subtract():
    add = getattr(Calculator, "add", None)
    sub = getattr(Calculator, "subtract", None)
    # If functions are not module-level, try methods on Calculator class
    if add is None or sub is None:
        CalcClass = getattr(Calculator, "Calculator", None)
        if CalcClass is not None:
            add = getattr(CalcClass, "add", add)
            sub = getattr(CalcClass, "subtract", sub)
            return add, sub, CalcClass
    return add, sub, None

def _open_interceptor(monkeypatch, recorder):
    """
    Monkeypatch builtins.open so that any open(...) returning a context manager writes into recorder dict.
    """
    fake = _FakeFile()

    def fake_open(file, mode="r", *args, **kwargs):
        # record the path and mode for assertions
        recorder["last_path"] = file
        recorder["last_mode"] = mode
        recorder["file_obj"] = fake
        return fake

    monkeypatch.setattr(builtins, "open", fake_open)

def test_calculator_add_subtract_basic_arithmetic_and_errors():
    
    # Arrange
    add, sub, CalcClass = _get_add_and_subtract()
    calc_error = getattr(Calculator, "CalculatorError", Exception)

    # Act / Assert for add/sub functions or methods
    if add is not None:
        # normal integers
        result = add(5, 7)
        assert isinstance(result, (int, float)), "add should return numeric type"
        assert result == 12

        # floats
        result = add(1.5, 2.25)
        assert abs(result - 3.75) < 1e-9

        
        with pytest.raises((calc_error, TypeError)):
            add("a", 2)
    else:
        pytest.skip("No add function/method found on Calculator")

    if sub is not None:
        result = sub(10, 3)
        assert result == 7
        result = sub(3.5, 0.5)
        assert abs(result - 3.0) < 1e-9

        with pytest.raises((calc_error, TypeError)):
            sub(None, 1)
    else:
        pytest.skip("No subtract function/method found on Calculator")

def test_simplecalculator_module_references_calculator_class():
    
    # Arrange / Act
    references = _module_references_calculator_class()

    # Assert - integration: GUI module should reference core Calculator class
    assert references is True, "SimpleCalculatorPyQt1 should reference the Calculator class from Calculator module"

def test_save_history_writes_expected_content(tmp_path, monkeypatch):
    
    # Arrange
    save_func = _find_save_func()
    if save_func is None:
        pytest.skip("No save_history callable found in SimpleCalculatorPyQt1 module or MainWindow class")

    # Inspect source to understand what attribute names might be used
    try:
        src = inspect.getsource(save_func)
    except (OSError, TypeError):
        # If source can't be retrieved, provide a basic dummy source guess
        src = ""

    # Prepare dummy history lines to be exported
    expected_lines = ["1 + 1 = 2", "3 - 2 = 1"]

    dummy = _make_dummy_window_for_save(src, expected_lines)

    # Intercept QFileDialog.getSaveFileName to avoid GUI dialogs and supply a file path
    path = str(tmp_path / "history_out.txt")
    # QFileDialog.getSaveFileName may return either a string or a tuple depending on PyQt version; handle both
    def fake_getsave(*args, **kwargs):
        return (path, "") if hasattr(QtWidgets.QFileDialog.getSaveFileName, "__call__") else path

    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", fake_getsave, raising=False)

    # Intercept builtins.open so that no real file is created and we can capture writes
    recorder = {}
    _open_interceptor(monkeypatch, recorder)

    # Act
    # call as unbound function if it's a method defined on class; ensure we pass the dummy as self
    try:
        # If save_func is a function defined on module level, calling with dummy may not accept a parameter;
        # attempt both ways: prefer bound style if it's function with one parameter in source.
        # Determine number of parameters
        params = None
        try:
            params = inspect.signature(save_func).parameters
        except (ValueError, TypeError):
            params = None

        if params and len(params) >= 1:
            # Unbound method style: pass dummy as self
            save_func(dummy)
        else:
            # Module-level helper possibly expects no args
            save_func()
    except TypeError:
        # Try alternative call (no args)
        save_func()

    # Assert
    # Ensure open was called and recorded something
    assert "file_obj" in recorder, "save_history should call open to write history content"

    written = recorder["file_obj"].read()
    assert isinstance(written, str), "Captured write content must be a string"

    # Each expected line should appear in the written content
    for line in expected_lines:
        assert line in written, f"Expected history line '{line}' not found in saved content"

    # The path recorded should match our fake dialog return
    assert recorder.get("last_path") is not None, "save_history should specify a path when opening a file"
    # last_mode should be a write mode
    assert "w" in recorder.get("last_mode", ""), "save_history should open the file for writing"
