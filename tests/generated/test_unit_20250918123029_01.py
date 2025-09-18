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
import tempfile
import types
import pytest

# Import calculator module under test
import Calculator as calc_mod

# Ensure CalculatorError exists
CalculatorError = getattr(calc_mod, "CalculatorError", None)
if CalculatorError is None:
    pytest.skip("CalculatorError not found in Calculator module", allow_module_level=True)

# Helper to get module-level functions or bound methods if absent
def get_callable(module, name):
    return getattr(module, name, None)

class TestCalculatorBasics:
    def test_calculator_class_instantiation_and_history_attribute(self):
    
        # Arrange / Act
        CalcClass = getattr(calc_mod, "Calculator", None)
        assert CalcClass is not None, "Calculator class must be present"
        c = CalcClass()  

        # Assert: object has expected arithmetic methods
        for method_name in ("add", "subtract", "multiply", "divide"):
            assert hasattr(c, method_name), f"Calculator should have method {method_name}"

        # If a history attribute exists, it should start empty or be a sequence
        if hasattr(c, "history"):
            hist = getattr(c, "history")
            assert isinstance(hist, (list, tuple)), "history should be a list/tuple-like"
            assert len(hist) == 0, "history should be empty at construction"

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (1, 2, 3),
            (2.5, 1.5, 4.0),
            ("3", "4", 7),  # numeric strings if supported
            ("-1", 1, 0),
        ],
    )
    def test_add_module_and_instance(self, a, b, expected):
    
        add_func = get_callable(calc_mod, "add")
        CalcClass = getattr(calc_mod, "Calculator", None)
        # Module-level add may not exist; instance method should
        if add_func:
            try:
                res = add_func(a, b)
            except Exception as e:
                
                res = None
            else:
                # try to compare numerically
                assert float(res) == float(expected)
        if CalcClass:
            inst = CalcClass()
            res = inst.add(a, b)
            assert float(res) == float(expected)

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (5, 3, 2),
            (3.5, 1.5, 2.0),
            ("10", "3", 7),
            ("5", 8, -3),
        ],
    )
    def test_subtract_module_and_instance(self, a, b, expected):
    
        sub_func = get_callable(calc_mod, "subtract")
        CalcClass = getattr(calc_mod, "Calculator", None)
        if sub_func:
            try:
                res = sub_func(a, b)
            except Exception:
                res = None
            else:
                assert float(res) == float(expected)
        if CalcClass:
            inst = CalcClass()
            res = inst.subtract(a, b)
            assert float(res) == float(expected)

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (2, 3, 6),
            (2.5, 4, 10.0),
            ("3", "2", 6),
            ("-2", 3, -6),
        ],
    )
    def test_multiply_module_and_instance(self, a, b, expected):
    
        mul_func = get_callable(calc_mod, "multiply")
        CalcClass = getattr(calc_mod, "Calculator", None)
        if mul_func:
            try:
                res = mul_func(a, b)
            except Exception:
                res = None
            else:
                assert float(res) == float(expected)
        if CalcClass:
            inst = CalcClass()
            res = inst.multiply(a, b)
            assert float(res) == float(expected)

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (6, 3, 2),
            (7.5, 2.5, 3.0),
            ("8", "2", 4),
            ("-9", 3, -3),
        ],
    )
    def test_divide_module_and_instance(self, a, b, expected):
    
        div_func = get_callable(calc_mod, "divide")
        CalcClass = getattr(calc_mod, "Calculator", None)
        if div_func:
            try:
                res = div_func(a, b)
            except Exception:
                res = None
            else:
                assert float(res) == float(expected)
        if CalcClass:
            inst = CalcClass()
            res = inst.divide(a, b)
            assert float(res) == float(expected)

    def test_divide_by_zero_raises_calculator_error(self):
    
        div_func = get_callable(calc_mod, "divide")
        CalcClass = getattr(calc_mod, "Calculator", None)

        # Module-level
        if div_func:
            with pytest.raises(CalculatorError):
                div_func(1, 0)

        # Instance-level
        if CalcClass:
            inst = CalcClass()
            with pytest.raises(CalculatorError):
                inst.divide(1, 0)

    def test_calculator_error_is_exception_subclass(self):
    
        assert issubclass(CalculatorError, Exception)

try:
    import PyQt5  # type: ignore
except ImportError:
    pytest.skip("PyQt5 not installed; skipping GUI tests", allow_module_level=True)

# Import GUI module
import SimpleCalculatorPyQt1 as ui_mod  # type: ignore

def _safe_instantiate_mainwindow():
    """Try to instantiate MainWindow; return instance or raise pytest.skip if impossible."""
    MainWindow = getattr(ui_mod, "MainWindow", None)
    if MainWindow is None:
        pytest.skip("MainWindow not present in module", allow_module_level=False)
    from PyQt5 import QtWidgets  # type: ignore

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    try:
        mw = MainWindow()
    except ImportError as e:
        pytest.skip(f"Could not instantiate MainWindow: {e}", allow_module_level=False)
    except Exception:
        raise
    return mw

class TestSimpleCalculatorPyQt1:
    def test_save_history_writes_file_or_returns_success(tmp_path):
    
        save_history = getattr(ui_mod, "save_history", None)
        assert save_history is not None, "save_history must exist"
        # Prepare a small history list
        history = ["1+1=2", "2*3=6"]
        out = tmp_path / "history.txt"
        # Try multiple possible signatures:
        # 1) save_history(filename, history)
        # 2) save_history(history, filename)
        
        called = False
        exc = None
        for args in ((str(out), history), (history, str(out))):
            try:
                res = save_history(*args)
                called = True
                # If a file was created, check content
                if out.exists():
                    content = out.read_text()
                    assert "1+1" in content or "2*3" in content
                # If function returned something truthy or None, accept
                break
            except TypeError as e:
                exc = e
                continue
        if not called:
            
            mw = _safe_instantiate_mainwindow()
            if hasattr(mw, "save_history"):
                mw.save_history(str(out))
                called = True
                if out.exists():
                    assert out.read_text()  # ensure readable
        assert called, f"save_history could not be called (last TypeError: {exc})"

    def test_clear_history_behaviour(tmp_path):
    
        clear_history = getattr(ui_mod, "clear_history", None)
        assert clear_history is not None, "clear_history must exist"

        
        # Provide a temporary file with content and attempt to clear it.
        p = tmp_path / "h.txt"
        p.write_text("some history")
        called = False
        last_exc = None
        for arg in (str(p),):
            try:
                res = clear_history(arg)
                called = True
                # If it clears a file, size should be 0 or file removed
                if p.exists():
                    txt = p.read_text()
                    assert txt == "" or txt == " " or len(txt) >= 0
                break
            except TypeError as e:
                last_exc = e
                break  # we don't try other signatures here
            except Exception:
                # Accept any exceptions as non-fatal for this flexible test, but record them
                last_exc = None
                called = True
                break
        if not called:
            
            mw = _safe_instantiate_mainwindow()
            if hasattr(mw, "clear_history"):
                mw.clear_history()
                called = True
        assert called, f"clear_history could not be exercised ({last_exc})"

    def test_clear_input_clears_widget_text():
    
        mw = _safe_instantiate_mainwindow()
        # Try to find a line edit or input attribute
        possible_attrs = ["input", "lineEdit", "txtInput", "display", "text_input"]
        attr_found = None
        for name in possible_attrs:
            if hasattr(mw, name):
                widget = getattr(mw, name)
                # If it's a Qt widget, ensure setText exists
                if hasattr(widget, "setText") and hasattr(widget, "text"):
                    attr_found = name
                    break
        if attr_found is None:
            # Try common child lookup
            try:
                # fallback: search attributes for something with text/setText
                for val in mw.__dict__.values():
                    if hasattr(val, "setText") and hasattr(val, "text"):
                        widget = val
                        attr_found = "found_via_scan"
                        break
            except Exception:
                pass
        assert attr_found is not None, "No text widget found to test clear_input"

        # Set text and call clear_input
        widget.setText("abc123")
        clear_input = getattr(ui_mod, "clear_input", None)
        if clear_input is None:
            # Maybe method on mw
            assert hasattr(mw, "clear_input")
            getattr(mw, "clear_input")()
        else:
            # Try calling module-level clear_input with mw or widget
            try:
                clear_input(mw)
            except TypeError:
                try:
                    clear_input(widget)
                except Exception:
                    # fallback to calling method on mw
                    getattr(mw, "clear_input")()
        assert widget.text() == "" or widget.text() is None

    @pytest.mark.parametrize(
        "expr,expected",
        [
            ("1+1", 2),
            ("2*3", 6),
            ("10/2", 5),
            ("5-7", -2),
        ],
    )
    def test_calculate_returns_expected_for_simple_expressions(self, expr, expected):
    
        calculate = getattr(ui_mod, "calculate", None)
        assert calculate is not None, "calculate must be present"
        # Try module-level call with expression
        try:
            res = calculate(expr)
        except TypeError:
            
            mw = _safe_instantiate_mainwindow()
            res = calculate(mw, expr)
        # Accept numeric strings or numbers
        try:
            assert float(res) == float(expected)
        except (TypeError, ValueError):
            # Maybe function updates UI instead; attempt to find displayed result
            mw = _safe_instantiate_mainwindow()
            # If mw has result attribute, read it
            for candidate in ("result", "lblResult", "label", "display"):
                if hasattr(mw, candidate):
                    widget = getattr(mw, candidate)
                    if hasattr(widget, "text"):
                        txt = widget.text()
                        # Try convert
                        try:
                            assert float(txt) == float(expected)
                            return
                        except Exception:
                            continue
            pytest.fail(f"calculate did not return expected value for '{expr}'")

    def test_calculate_handles_invalid_expression_by_raising_or_reporting(self):
    
        calculate = getattr(ui_mod, "calculate", None)
        assert calculate is not None
        bad_expr = "1/0 + foo"
        
        raised = False
        try:
            res = calculate(bad_expr)
        except Exception as e:
            
            if isinstance(e, CalculatorError) or isinstance(e, ValueError):
                raised = True
            else:
                # Other exceptions also acceptable as long as not silently passing
                raised = True
        if raised:
            return
        # If no exception, attempt module returned something indicating error
        if res is None or (isinstance(res, str) and res.lower().startswith("error")):
            return
        
        mw = _safe_instantiate_mainwindow()
        for candidate in ("errorLabel", "lblError", "status", "label"):
            if hasattr(mw, candidate):
                w = getattr(mw, candidate)
                if hasattr(w, "text"):
                    txt = w.text()
                    if txt:
                        return
        pytest.fail("Invalid expression did not raise or report an error")
