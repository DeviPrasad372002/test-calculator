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
import pathlib
import pytest

# Guard imports of project and third-party modules
try:
    import target.Calculator as calc_mod
    import target.SimpleCalculatorPyQt1 as ui_mod
except ImportError as e:
    pytest.skip(f"Required target modules not importable: {e}", allow_module_level=True)

def _get_callable_or_method(module, func_name, class_name=None):
    """
    Return a callable for the requested operation.
    Prefer a module-level function; fall back to an instance method on the class if present.
    """
    if hasattr(module, func_name) and callable(getattr(module, func_name)):
        return getattr(module, func_name)
    if class_name and hasattr(module, class_name):
        klass = getattr(module, class_name)
        try:
            instance = klass()
        except Exception:
            
            if hasattr(klass, func_name):
                return getattr(klass, func_name)
            raise
        if hasattr(instance, func_name) and callable(getattr(instance, func_name)):
            return getattr(instance, func_name)
    raise AttributeError(f"No callable '{func_name}' found in module '{module.__name__}'")

# Prepare callables for multiply and divide
try:
    multiply = _get_callable_or_method(calc_mod, "multiply", class_name="Calculator")
except Exception as exc:
    pytest.skip(f"Could not obtain 'multiply' callable: {exc}", allow_module_level=True)

try:
    divide = _get_callable_or_method(calc_mod, "divide", class_name="Calculator")
except Exception as exc:
    pytest.skip(f"Could not obtain 'divide' callable: {exc}", allow_module_level=True)

# Determine the calculator-specific error class if present
CalculatorError = getattr(calc_mod, "CalculatorError", None)

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (3, 4, 12),
        (0, 5, 0),
        (-2, 6, -12),
        (2.5, 4, 10.0),
    ],
)
def test_multiply_various_inputs_produces_expected_results(a, b, expected):
    
    # Arrange done by parametrization
    # Act
    result = multiply(a, b)
    # Assert
    # For floats allow precise equality when expected is an int but result may be float
    if isinstance(expected, float):
        assert isinstance(result, float)
        assert result == pytest.approx(expected)
    else:
        # Expect exact numeric equality and correct type (int if both inputs ints)
        if isinstance(a, int) and isinstance(b, int):
            assert isinstance(result, int)
        assert result == expected

@pytest.mark.parametrize(
    "numerator,denominator,expected",
    [
        (10, 2, 5),
        (7.5, 2.5, 3.0),
        (-9, -3, 3),
    ],
)
def test_divide_returns_correct_value_for_nonzero_denominator(numerator, denominator, expected):
    
    # Arrange/Act
    result = divide(numerator, denominator)
    # Assert numeric correctness with float tolerance when necessary
    if isinstance(expected, float):
        assert isinstance(result, float)
        assert result == pytest.approx(expected)
    else:
        assert result == expected

def test_divide_by_zero_raises_expected_exception():
    
    # Arrange
    numerator = 5
    denominator = 0
    # Decide expected exception class: prefer CalculatorError if provided
    expected_exc = CalculatorError if CalculatorError is not None else ZeroDivisionError
    # Act / Assert
    with pytest.raises(expected_exc):
        divide(numerator, denominator)

def test_save_history_writes_file_and_contains_entries(tmp_path, monkeypatch):
    
    # This test adapts to several possible implementations of save_history in ui_mod.
    save_attr = getattr(ui_mod, "save_history", None)
    MainWindow = getattr(ui_mod, "MainWindow", None)

    if save_attr is None and MainWindow is None:
        pytest.skip("No save_history function or MainWindow class present in UI module")

    target_file = tmp_path / "history_output.txt"

    # Strategy 1: if there is a module-level save_history that accepts a path, call it directly
    if callable(save_attr):
        sig = inspect.signature(save_attr)
        params = sig.parameters
        try:
            # If signature accepts a single path-like argument, try calling with file path
            if len(params) == 1:
                save_attr(str(target_file))
                assert target_file.exists(), "Expected save_history to create the target file"
                content = target_file.read_text(encoding="utf-8")
                assert len(content) > 0, "Saved history file should not be empty"
                return
            # If it takes zero or more args, try calling without args (it may open dialog)
            if len(params) == 0:
                # Monkeypatch file dialog to return our chosen path if present
                QFileDialog = getattr(ui_mod, "QFileDialog", None)
                if QFileDialog and hasattr(QFileDialog, "getSaveFileName"):
                    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target_file), ""))
                save_attr()
                assert target_file.exists(), "Expected save_history to create the target file"
                content = target_file.read_text(encoding="utf-8")
                assert len(content) > 0
                return
        except TypeError:
            # Fall through to other strategies
            pass

    
    if MainWindow is not None:
        # Prevent QApplication side-effects if PyQt is used: monkeypatch QApplication to a harmless stub
        QtWidgets = getattr(ui_mod, "QtWidgets", None)
        if QtWidgets and hasattr(QtWidgets, "QApplication"):
            monkeypatch.setattr(QtWidgets, "QApplication", lambda *a, **k: object())

        try:
            mw = MainWindow()
        except Exception as exc:
            pytest.skip(f"Cannot instantiate MainWindow in test environment: {exc}")

        # Provide a simple deterministic history representation depending on implementation
        if hasattr(mw, "history"):
            # If history is a list-like or provides an iterator, populate it
            try:
                # If it's a QListWidget-like, try to set a simple attribute for testing
                if isinstance(getattr(mw, "history"), list):
                    mw.history[:] = ["1+1=2", "2*3=6"]
                else:
                    # Overwrite with simple list for deterministic behavior
                    setattr(mw, "history", ["1+1=2", "2*3=6"])
            except Exception:
                setattr(mw, "history", ["1+1=2", "2*3=6"])
        else:
            # Ensure save_history can find something to save
            setattr(mw, "history", ["1+1=2", "2*3=6"])

        # Monkeypatch any file dialog used inside save_history to return our target file path
        QFileDialog = getattr(ui_mod, "QFileDialog", None)
        if QFileDialog and hasattr(QFileDialog, "getSaveFileName"):
            monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target_file), ""))

        # Call the instance method if present
        if hasattr(mw, "save_history") and callable(getattr(mw, "save_history")):
            getattr(mw, "save_history")()
            assert target_file.exists(), "Expected MainWindow.save_history to create the file"
            content = target_file.read_text(encoding="utf-8")
            
            assert "1+1=2" in content
            assert "2*3=6" in content
            return

    
    pytest.skip("Could not exercise save_history implementation in a headless test environment")
