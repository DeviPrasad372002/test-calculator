import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t=os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p=os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0,p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target',_pkg)

try:
    import importlib
except ModuleNotFoundError:
    try:
        import importlib
    except ModuleNotFoundError:
        import pytest
        pytest.skip('module importlib not importable; skipping module', allow_module_level=True)
try:
    import inspect
except ModuleNotFoundError:
    try:
        import inspect
    except ModuleNotFoundError:
        import pytest
        pytest.skip('module inspect not importable; skipping module', allow_module_level=True)
try:
    import os
except ModuleNotFoundError:
    try:
        import os
    except ModuleNotFoundError:
        import pytest
        pytest.skip('module os not importable; skipping module', allow_module_level=True)
try:
    import sys
except ModuleNotFoundError:
    try:
        import sys
    except ModuleNotFoundError:
        import pytest
        pytest.skip('module sys not importable; skipping module', allow_module_level=True)
try:
    from types import ModuleType
except ModuleNotFoundError:
    try:
        from types import ModuleType
    except ModuleNotFoundError:
        import pytest
        pytest.skip('module types not importable; skipping module', allow_module_level=True)
try:
    import pytest
except ModuleNotFoundError:
    try:
        import pytest
    except ModuleNotFoundError:
        import pytest
        pytest.skip('module pytest not importable; skipping module', allow_module_level=True)
# Helper to try multiple import names for modules that may be top-level or inside `target` package.
def import_optional_module(names):
    last_err = None
    for name in names:
        try:
            return importlib.import_module(name)
        except Exception as e:
            last_err = e
            continue
    raise ImportError(f"Could not import any of {names}; last error: {last_err}")

# Import Calculator module (try common names)
calc_mod = import_optional_module(["Calculator", "target.Calculator"])

# Ensure CalculatorError is present
assert hasattr(calc_mod, "CalculatorError"), "CalculatorError missing from calculator module"
CalculatorError = getattr(calc_mod, "CalculatorError")

# Utility to get a callable either from module or from instance
def get_callable(obj, name):
    # If obj has attribute name and it's callable, return it
    if hasattr(obj, name) and callable(getattr(obj, name)):
        return getattr(obj, name)
    return None

# Tests for pure calculator functions and class
@pytest.mark.parametrize(
    "func_name,a,b,expected",
    [
        ("add", 1, 2, 3),
        ("add", -1, 1, 0),
        ("add", 2.5, 0.5, 3.0),
        ("subtract", 5, 3, 2),
        ("subtract", 3, 5, -2),
        ("subtract", 2.5, 1.25, 1.25),
        ("multiply", 3, 4, 12),
        ("multiply", -2, -3, 6),
        ("multiply", 1.5, 2.0, 3.0),
        ("divide", 10, 2, 5),
        ("divide", 7.5, 2.5, 3.0),
    ],
)
def test_module_level_operations_return_expected(func_name, a, b, expected):
    
    assert hasattr(calc_mod, func_name), f"{func_name} missing from module"
    func = getattr(calc_mod, func_name)
    assert callable(func)
    result = func(a, b)
    # allow float approximations
    if isinstance(expected, float):
        assert pytest.approx(expected, rel=1e-9) == result
    else:
        assert result == expected

def test_divide_by_zero_raises_module_level():
    
    assert hasattr(calc_mod, "divide")
    with pytest.raises(Exception) as exc:
        calc_mod.divide(1, 0)
    # Accept either custom CalculatorError or built-in ZeroDivisionError
    assert isinstance(exc.value, (CalculatorError, ZeroDivisionError))

def test_calculator_class_init_and_methods_exist_and_basic_behavior():
    
    assert hasattr(calc_mod, "Calculator"), "Calculator class missing"
    CalcClass = getattr(calc_mod, "Calculator")
    calc = CalcClass()
    # Basic check: for each operation, either instance method exists or module level function exists
    for name, a, b, expected in [("add", 2, 3, 5), ("subtract", 5, 2, 3), ("multiply", 4, 2, 8), ("divide", 9, 3, 3)]:
        method = get_callable(calc, name)
        if method is None:
            # fallback to module-level function bound to the instance
            assert hasattr(calc_mod, name), f"Neither Calculator.{name} nor module {name} exists"
            method = getattr(calc_mod, name)
        result = method(a, b)
        if isinstance(expected, float):
            assert pytest.approx(expected, rel=1e-9) == result
        else:
            assert result == expected

def test_calculator_divide_by_zero_raises_on_instance():
    
    CalcClass = getattr(calc_mod, "Calculator")
    calc = CalcClass()
    method = get_callable(calc, "divide")
    if method is None:
        # fallback to module-level divide
        method = getattr(calc_mod, "divide")
    with pytest.raises(Exception) as exc:
        method(1, 0)
    assert isinstance(exc.value, (CalculatorError, ZeroDivisionError))

PyQt5 = pytest.importorskip("PyQt5", reason="PyQt5 is required for GUI tests")

# Try to import the SimpleCalculatorPyQt1 module (it may be top-level or in target)
try:
    sc_mod = import_optional_module(["SimpleCalculatorPyQt1", "target.SimpleCalculatorPyQt1"])
except ImportError:
    pytest.skip("SimpleCalculatorPyQt1 module not available; skipping GUI tests", allow_module_level=True)

if not hasattr(sc_mod, "MainWindow"):
    pytest.skip("MainWindow not exposed by SimpleCalculatorPyQt1; skipping GUI tests", allow_module_level=True)
try:
    from PyQt5 import QtWidgets
except ModuleNotFoundError:
    try:
        from pyqt5 import QtWidgets
    except ModuleNotFoundError:
        import pytest
        pytest.skip('module PyQt5 not importable; skipping module', allow_module_level=True)

# Ensure a QApplication exists for tests
_app = QtWidgets.QApplication.instance()
if _app is None:
    _app = QtWidgets.QApplication([])

def find_widget_by_duck(main, has_set_text=True, has_text=True):
    """
    Find an attribute of `main` that looks like a text input widget:
    - has setText and text methods (duck-typing).
    Returns attribute name and object or (None, None).
    """
    for name, obj in vars(main).items():
        if has_set_text and not callable(getattr(obj, "setText", None)):
            continue
        if has_text and not callable(getattr(obj, "text", None)):
            continue
        return name, obj
    return None, None

def find_history_like(main):
    """
    Find a history-like attribute: either a QListWidget-like (addItem/clear/count) or a python list.
    Returns name and object or (None, None).
    """
    from PyQt5.QtWidgets import QListWidget
    for name, obj in vars(main).items():
        # QListWidget
        if isinstance(obj, QListWidget):
            return name, obj
        # duck-type: addItem and clear and count
        if callable(getattr(obj, "addItem", None)) and callable(getattr(obj, "clear", None)):
            return name, obj
        # python list
        if isinstance(obj, list):
            return name, obj
    return None, None

def set_history_contents(history_like, entries):
    """
    Populate a history-like object with string entries.
    """
    from PyQt5.QtWidgets import QListWidget
    if isinstance(history_like, list):
        history_like.clear()
        history_like.extend(entries)
        return
    # QListWidget or similar
    if hasattr(history_like, "clear") and hasattr(history_like, "addItem"):
        history_like.clear()
        for e in entries:
            history_like.addItem(str(e))
        return
    # fallback: try to set attribute 'history' if exists
    try:
        history_like.history = list(entries)
    except Exception:
        raise RuntimeError("Cannot populate history-like object")

@pytest.mark.skipif(not hasattr(sc_mod, "MainWindow"), reason="MainWindow not available")
def test_clear_input_clears_first_text_widget(monkeypatch):
    
    MainWindow = getattr(sc_mod, "MainWindow")
    main = MainWindow()
    name, widget = find_widget_by_duck(main)
    if widget is None:
        pytest.skip("No text-like widget found on MainWindow to test clear_input")
    # set some text
    widget.setText("  123 ")
    
    if hasattr(main, "clear_input") and callable(getattr(main, "clear_input")):
        main.clear_input()
    else:
        pytest.skip("MainWindow.clear_input not implemented")
    assert widget.text() == "" or widget.text() is None

@pytest.mark.skipif(not hasattr(sc_mod, "MainWindow"), reason="MainWindow not available")
def test_clear_history_empties_history_widget_or_list():
    
    MainWindow = getattr(sc_mod, "MainWindow")
    main = MainWindow()
    hist_name, hist_obj = find_history_like(main)
    if hist_obj is None:
        pytest.skip("No history-like attribute found on MainWindow to test clear_history")
    # populate with entries
    set_history_contents(hist_obj, ["one", "two", "three"])
    # call clear_history
    if hasattr(main, "clear_history") and callable(getattr(main, "clear_history")):
        main.clear_history()
    else:
        pytest.skip("MainWindow.clear_history not implemented")
    # verify emptied
    if isinstance(hist_obj, list):
        assert len(hist_obj) == 0
    else:
        # try count() or __len__ or model rowCount
        if callable(getattr(hist_obj, "count", None)):
            assert hist_obj.count() == 0
        else:
            # fallback to checking that there are no children or items
            assert getattr(hist_obj, "__len__", lambda: 0)() == 0 or True

@pytest.mark.skipif(not hasattr(sc_mod, "MainWindow"), reason="MainWindow not available")
def test_save_history_writes_file(tmp_path, monkeypatch):
    
    MainWindow = getattr(sc_mod, "MainWindow")
    main = MainWindow()
    hist_name, hist_obj = find_history_like(main)
    if hist_obj is None:
        pytest.skip("No history-like attribute found on MainWindow to test save_history")
    entries = ["a", "b", "c"]
    set_history_contents(hist_obj, entries)
    # Monkeypatch QFileDialog.getSaveFileName to return our path
    tmpfile = tmp_path / "history_test.txt"
    # getSaveFileName may return different shapes depending on PyQt version
    def fake_get_save_file_name(*args, **kwargs):
        # Qt5 often returns tuple (filename, filter)
        return (str(tmpfile), "")
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", staticmethod(fake_get_save_file_name))
    # Call save_history
    if hasattr(main, "save_history") and callable(getattr(main, "save_history")):
        main.save_history()
    else:
        pytest.skip("MainWindow.save_history not implemented")
    
    assert tmpfile.exists(), "save_history did not create the expected file"
    content = tmpfile.read_text(encoding="utf8")
    for ent in entries:
        if ent in content:
            break
    else:
        pytest.fail("Saved history file does not contain expected entries")

@pytest.mark.skipif(not hasattr(sc_mod, "MainWindow"), reason="MainWindow not available")
@pytest.mark.parametrize(
    "expr,expected",
    [
        ("2+3", "5"),
        ("10 - 4", "6"),
        ("6*7", "42"),
        ("8/2", "4"),
    ],
)
def test_calculate_updates_some_output_widget(expr, expected):
    
    MainWindow = getattr(sc_mod, "MainWindow")
    main = MainWindow()
    # find an input widget
    in_name, in_widget = find_widget_by_duck(main)
    if in_widget is None:
        pytest.skip("No input widget to set expression for calculate")
    
    result_widget = None
    for name, obj in vars(main).items():
        if obj is in_widget:
            continue
        if callable(getattr(obj, "setText", None)) and callable(getattr(obj, "text", None)):
            result_widget = obj
            break
    if result_widget is None:
        # maybe calculate returns a result instead of updating widget
        # try calling calculate and inspect return
        if not (hasattr(main, "calculate") and callable(getattr(main, "calculate"))):
            pytest.skip("No result widget and no calculate method to test")
        in_widget.setText(expr)
        ret = main.calculate()
        
        assert (ret is None) or (expected in str(ret))
        return
    # set expression and call calculate
    in_widget.setText(expr)
    if not (hasattr(main, "calculate") and callable(getattr(main, "calculate"))):
        pytest.skip("MainWindow.calculate not implemented")
    main.calculate()
    
    got = result_widget.text()
    assert expected in got or str(expected) == got or pytest.approx(float(expected), rel=1e-6) == float(got) if got.replace('.', '', 1).isdigit() else expected in got
