
# --- ENHANCED UNIVERSAL BOOTSTRAP ---
import os, sys, importlib.util as _iu, types as _types, pytest as _pytest, builtins as _builtins, warnings
STRICT = os.getenv("TESTGEN_STRICT", "1").lower() in ("1","true","yes")
STRICT_FAIL = os.getenv("TESTGEN_STRICT_FAIL","0").lower() in ("1","true","yes")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

_target = os.environ.get("TARGET_ROOT") or os.environ.get("ANALYZE_ROOT") or "target"
if _target and os.path.isdir(_target):
    _parent = os.path.abspath(os.path.join(_target, os.pardir))
    for p in (_parent, _target):
        if p not in sys.path:
            sys.path.insert(0, p)
    if "target" not in sys.modules:
        _pkg = _types.ModuleType("target")
        _pkg.__path__ = [_target]  # behave like a namespace package
        sys.modules["target"] = _pkg

def _exc_lookup(name, default):
    try:
        mod_name, _, cls_name = str(name).rpartition(".")
        if mod_name:
            mod = __import__(mod_name, fromlist=[cls_name])
            return getattr(mod, cls_name, default)
        return getattr(sys.modules.get("builtins"), str(name), default)
    except Exception:
        return default

# Optional Django bootstrap to avoid masking real failures by default.
if os.getenv("TESTGEN_ENABLE_DJANGO_BOOTSTRAP","0") in ("1","true","yes"):
    try:
        import django
        from django.conf import settings as _dj_settings
        from django import apps as _dj_apps
        if not _dj_settings.configured:
            _cfg = dict(
                DEBUG=True, SECRET_KEY='pytest-secret',
                DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3','NAME': ':memory:'}},
                INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages'],
                MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware'],
                USE_TZ=True, TIME_ZONE='UTC',
            )
            try: _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
            except Exception: pass
            try: _dj_settings.configure(**_cfg)
            except Exception: pass
        if not _dj_apps.ready:
            try: django.setup()
            except Exception: pass
        try: import django.contrib.auth.base_user as _dj_probe  # noqa
        except Exception as _e:
            _pytest.skip(f"Django core import failed safely: {_e.__class__.__name__}: {_e}", allow_module_level=True)
    except Exception as _e:
        _pytest.skip(f"Django bootstrap not available: {_e.__class__.__name__}: {_e}", allow_module_level=True)

import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
for __qt_root in ['PyQt5','PyQt6','PySide2','PySide6']:
    try:
        import importlib.util as _iu
        if _iu.find_spec(__qt_root) is None:
            raise ImportError
    except Exception:
        pass
# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

import pytest
import os
from pathlib import Path
from unittest import mock

try:
    import Calculator
    import SimpleCalculatorPyQt1 as appmod
    from PyQt5 import QtWidgets
except ImportError as e:
    pytest.skip("Missing dependency for GUI tests: %s" % e, allow_module_level=True)


def _ensure_qapp():
    # Arrange: Ensure a single QApplication exists for widget tests.
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def _find_widget_by_capabilities(obj, need_set=False, need_get=False, need_append=False):
    """
    Heuristic: scan attributes on obj to find a widget-like object that supports required capabilities.
    need_set -> setText or setPlainText
    need_get -> text or toPlainText
    need_append -> append
    Returns attribute name and the object.
    """
    for name in dir(obj):
        if name.startswith('_'):
            continue
        try:
            attr = getattr(obj, name)
        except Exception:
            continue
        # skip callables and modules
        if callable(attr):
            continue
        has_set = callable(getattr(attr, "setText", None)) or callable(getattr(attr, "setPlainText", None))
        has_get = callable(getattr(attr, "text", None)) or callable(getattr(attr, "toPlainText", None))
        has_append = callable(getattr(attr, "append", None))
        ok = True
        if need_set and not has_set:
            ok = False
        if need_get and not has_get:
            ok = False
        if need_append and not has_append:
            ok = False
        if ok and (has_set or has_get or has_append):
            return name, attr
    return None, None


def _get_text(widget):
    if widget is None:
        return None
    if callable(getattr(widget, "toPlainText", None)):
        return widget.toPlainText()
    if callable(getattr(widget, "text", None)):
        return widget.text()
    return None


def _set_text(widget, value):
    if widget is None:
        return
    if callable(getattr(widget, "setText", None)):
        widget.setText(str(value))
    elif callable(getattr(widget, "setPlainText", None)):
        widget.setPlainText(str(value))


@pytest.mark.parametrize("initial_value", ["42", "", "   "])
def test_clear_input_clears_input_widget(initial_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    _ensure_qapp()
    # Create MainWindow instance from public API
    mw_cls = getattr(appmod, "MainWindow", None)
    assert mw_cls is not None, "MainWindow not found in module public API"
    mw = mw_cls()

    # Find an input-like widget: supports setText and text/toPlainText
    name, widget = _find_widget_by_capabilities(mw, need_set=True, need_get=True)
    assert widget is not None, "No input-like widget found on MainWindow instance (public API changed)"
    # Put initial content
    _set_text(widget, initial_value)
    assert _get_text(widget) is not None  # sanity

    # Act: call clear_input function if provided, else call method on instance
    clear_input_func = getattr(appmod, "clear_input", None)
    if callable(clear_input_func):
        clear_input_func(mw)
    else:
        clear_method = getattr(mw, "clear_input", None)
        assert callable(clear_method), "No clear_input function or MainWindow.clear_input method available"
        clear_method()

    # Assert: widget text is empty string after clear
    final = _get_text(widget)
    assert final in ("", None) or (isinstance(final, str) and final.strip() == ""), "Input was not cleared"


def test_save_history_writes_file_and_clear_history_empties_widget(tmp_path):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    _ensure_qapp()
    mw_cls = getattr(appmod, "MainWindow", None)
    assert mw_cls is not None
    mw = mw_cls()

    # find a history-like widget that supports append and toPlainText/text
    name_hist, hist_widget = _find_widget_by_capabilities(mw, need_append=True, need_get=True)
    # It's possible history is represented by a widget without 'append' (e.g., a QLabel). Fallback to any text-capable widget.
    if hist_widget is None:
        name_hist, hist_widget = _find_widget_by_capabilities(mw, need_get=True)
    assert hist_widget is not None, "No history-like widget found on MainWindow"

    # Add a deterministic history entry using public API: try calling a public calculate function if available
    # Attempt to use module-level calculate(expression) if present, else try instance method calculate
    sample_expr = "7+8"
    # First try to call module.calculate with an expression argument if possible
    calc_mod_fn = getattr(appmod, "calculate", None)
    used_calc = False
    if callable(calc_mod_fn):
        try:
            # Some calculate functions expect (mainwindow,) or (expression,)
            try:
                # prefer string invocation
                calc_mod_fn(sample_expr)
                used_calc = True
            except TypeError:
                # maybe expects MainWindow instance
                calc_mod_fn(mw)
                used_calc = True
        except Exception:
            # If calling calculate raised, append entry directly to history to simulate prior calculation
            used_calc = False

    if not used_calc:
        # Directly append a deterministic line to history widget (public widget API)
        if callable(getattr(hist_widget, "append", None)):
            hist_widget.append("calc: " + sample_expr + " = 15")
        elif callable(getattr(hist_widget, "setPlainText", None)):
            hist_widget.setPlainText("calc: " + sample_expr + " = 15")
        elif callable(getattr(hist_widget, "setText", None)):
            hist_widget.setText("calc: " + sample_expr + " = 15")
        else:
            pytest.skip("Unable to populate history via public API")

    # Ensure history has our sample content
    content_before = _get_text(hist_widget)
    assert content_before is not None and ("7" in content_before or "15" in content_before), "History did not contain expected entry"

    # Act: save history to a temporary file using public API
    dest = tmp_path / "history_out.txt"
    save_fn = getattr(appmod, "save_history", None)
    if callable(save_fn):
        # try save_history(mw, path) or save_history(path, mw)
        try:
            save_fn(mw, str(dest))
        except TypeError:
            save_fn(str(dest), mw)
    else:
        # fallback: if MainWindow provides save_history method
        mw_save = getattr(mw, "save_history", None)
        assert callable(mw_save), "No save_history function or method available in public API"
        mw_save(str(dest))

    # Assert: file exists and contains part of the history text
    assert dest.exists(), "save_history did not create the expected file"
    file_text = dest.read_text(encoding="utf-8")
    assert file_text is not None and len(file_text) > 0
    # The file should contain something from the in-memory history
    assert any(token in file_text for token in ("7", "15", "calc")), "Saved history file content does not match displayed history"

    # Act: clear history via public API
    clear_hist_fn = getattr(appmod, "clear_history", None)
    if callable(clear_hist_fn):
        clear_hist_fn(mw)
    else:
        mw_clear = getattr(mw, "clear_history", None)
        assert callable(mw_clear), "No clear_history function or MainWindow.clear_history method available"
        mw_clear()

    # Assert: history widget is empty or only whitespace
    final_hist = _get_text(hist_widget)
    assert final_hist in ("", None) or (isinstance(final_hist, str) and final_hist.strip() == ""), "History widget was not cleared"


def test_calculate_division_by_zero_reports_error_or_raises():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    _ensure_qapp()
    # First confirm Calculator.divide raises on divide by zero (unit-level contract)
    divide_fn = getattr(Calculator, "divide", None)
    expected_exc = getattr(Calculator, "CalculatorError", ZeroDivisionError)
    if callable(divide_fn):
        with pytest.raises(expected_exc):
            divide_fn(1, 0)

    # Now exercise the end-to-end calculate exposed by the GUI layer.
    mw_cls = getattr(appmod, "MainWindow", None)
    assert mw_cls is not None
    mw = mw_cls()

    # Try to find a result-like widget to inspect error messages; fallback to history
    _, result_widget = _find_widget_by_capabilities(mw, need_get=True)
    _, hist_widget = _find_widget_by_capabilities(mw, need_get=True)

    # Prepare input: try module.calculate with expression, otherwise set input widget and call instance calculate
    calc_mod = getattr(appmod, "calculate", None)
    used = False
    if callable(calc_mod):
        # Try calling as calculate("1/0")
        try:
            calc_mod("1/0")
            used = True
        except TypeError:
            # maybe expects MainWindow instance
            try:
                calc_mod(mw)
                used = True
            except Exception:
                used = False
        except Exception as exc:
            # If it raised, ensure it's an allowed error type
            assert isinstance(exc, expected_exc) or isinstance(exc, ZeroDivisionError)
            return  # test satisfied by raising correct error type

    if not used:
        # Set an input-like widget to "1/0" then call instance calculate
        name_inp, inp_widget = _find_widget_by_capabilities(mw, need_set=True, need_get=True)
        if inp_widget is None:
            pytest.skip("Cannot find input widget to set expression for calculate")
        _set_text(inp_widget, "1/0")
        inst_calc = getattr(mw, "calculate", None)
        if not callable(inst_calc):
            pytest.skip("No callable calculate on module or MainWindow to perform end-to-end calculation")
        try:
            inst_calc()
        except Exception as exc:
            # Accept either CalculatorError or ZeroDivisionError
            assert isinstance(exc, expected_exc) or isinstance(exc, ZeroDivisionError)
            return

    # If calculate returned/handled internally, assert that the UI shows an error indication
    # Look for error-like substrings in result or history widget
    candidates = []
    if result_widget is not None:
        candidates.append(_get_text(result_widget))
    if hist_widget is not None:
        candidates.append(_get_text(hist_widget))
    combined = " ".join([c for c in candidates if c])
    assert combined != "", "No output produced by calculate to inspect for error reporting"

    # Accept either explicit "error" message or words about division/zero
    lowered = combined.lower()
    assert any(token in lowered for token in ("error", "divide", "division", "zero", "cannot", "invalid")), (
        "Calculate did not raise and did not report an error in UI widgets; observed text: %r" % combined
    )
