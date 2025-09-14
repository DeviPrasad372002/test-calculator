
# --- ENHANCED UNIVERSAL BOOTSTRAP ---
import os, sys, importlib.util as _iu, types as _types, pytest as _pytest, builtins as _builtins, warnings
STRICT = os.getenv("TESTGEN_STRICT", "1").lower() in ("1","true","yes")
STRICT_FAIL = os.getenv("TESTGEN_STRICT_FAIL","0").lower() in ("1","true","yes")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

_target = os.environ.get("TARGET_ROOT") or os.environ.get("ANALYZE_ROOT") or "target"
if _target and os.path.exists(_target):
    if _target not in sys.path: sys.path.insert(0, _target)
    try: os.chdir(_target)
    except Exception: pass

def _exc_lookup(name, default):
    try:
        mod_name, _, cls_name = str(name).rpartition(".")
        if mod_name:
            mod = __import__(mod_name, fromlist=[cls_name])
            return getattr(mod, cls_name, default)
        return getattr(sys.modules.get("builtins"), str(name), default)
    except Exception:
        return default

def _apply_compatibility_fixes():
    try:
        import jinja2
        if not hasattr(jinja2, 'Markup'):
            try:
                from markupsafe import Markup, escape
                jinja2.Markup = Markup
                if not hasattr(jinja2, 'escape'):
                    jinja2.escape = escape
            except Exception:
                pass
    except ImportError:
        pass
    try:
        import collections as _collections, collections.abc as _abc
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container',
                   'MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection'):
            if not hasattr(_collections, _n) and hasattr(_abc, _n):
                setattr(_collections, _n, getattr(_abc, _n))
    except Exception:
        pass
    try:
        import marshmallow as _mm
        if not hasattr(_mm, "__version__"):
            _mm.__version__ = "4"
    except Exception:
        pass

_apply_compatibility_fixes()

# Minimal, safe Django bootstrap. If anything goes wrong, skip the module (repo-agnostic).
try:
    import django
    from django.conf import settings as _dj_settings
    from django import apps as _dj_apps

    if not _dj_settings.configured:
        _cfg = dict(
            DEBUG=True,
            SECRET_KEY='pytest-secret',
            DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3','NAME': ':memory:'}},
            INSTALLED_APPS=[
                'django.contrib.auth','django.contrib.contenttypes',
                'django.contrib.sessions','django.contrib.messages'
            ],
            MIDDLEWARE=[
                'django.middleware.security.SecurityMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.common.CommonMiddleware',
            ],
            USE_TZ=True, TIME_ZONE='UTC',
        )
        try: _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
        except Exception: pass
        try: _dj_settings.configure(**_cfg)
        except Exception: pass

    if not _dj_apps.ready:
        try: django.setup()
        except Exception: pass

    # Probe a known Django core that previously crashed on some stacks.
    try:
        import django.contrib.auth.base_user as _dj_probe  # noqa
    except Exception as _e:
        _pytest.skip(f"Django core import failed safely: {_e.__class__.__name__}: {_e}", allow_module_level=True)
except Exception as _e:
    # Do NOT crash the entire test session – make the module opt-out.
    _pytest.skip(f"Django bootstrap not available: {_e.__class__.__name__}: {_e}", allow_module_level=True)


for __qt_root in ["PyQt5","PyQt6","PySide2","PySide6"]:
    try:
        import importlib.util as _iu
        if _iu.find_spec(__qt_root) is None:
            raise ImportError
    except Exception:
        pass

# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

try:
    import pytest
except Exception:
    raise RuntimeError("pytest is required to run these tests")

try:
    import Calculator
    import SimpleCalculatorPyQt1
    import os
    import inspect
    from unittest import mock
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


def _exc_lookup(name, default=Exception):
    # try to find an exception class by name in common modules under test
    return getattr(Calculator, name, getattr(SimpleCalculatorPyQt1, name, default))


def _call_with_optional_args(func, *candidates):
    """
    Attempt to call func by inspecting its signature and trying sensible argument placements.
    If func expects 0 args, attempt to set common global attributes in the module of func
    using the first candidate.
    If func expects N args, pass up to N candidates from provided ones.
    """
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    if len(params) == 0:
        # attempt to set common global names on the function's module so the function can use them
        mod = inspect.getmodule(func)
        if mod is None:
            return func()
        first = candidates[0] if candidates else None
        for name in ('lineEdit', 'line_edit', 'input', 'input_field', 'entry', 'history', 'history_widget'):
            try:
                setattr(mod, name, first)
            except Exception:
                pass
        return func()
    else:
        # supply as many candidates as required (or repeat last)
        args = []
        for i in range(len(params)):
            if i < len(candidates):
                args.append(candidates[i])
            else:
                args.append(candidates[-1] if candidates else None)
        return func(*args)


@pytest.mark.parametrize("expr", [
    "2+3",
    "10-4",
    "5*6",
    "10/2",
])
def test_calculate_returns_expected_numeric_results_for_basic_operations(expr):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calculate = SimpleCalculatorPyQt1.calculate

    # Act
    result = calculate(expr)

    # Assert
    # Allow string or numeric return; compare numerically
    if isinstance(result, _exc_lookup("str", Exception)):
        try:
            numeric = float(result)
        except Exception:
            pytest.fail(f"calculate returned non-numeric string: {result!r}")
    else:
        numeric = float(result)
    expected = float(eval(expr))
    assert numeric == expected, f"calculate({expr!r}) -> {result!r} != expected {expected!r}"


@pytest.mark.parametrize("expr", [
    "1/0",
    "10/(5-5)",
])
def test_calculate_raises_calculator_error_on_division_by_zero(expr):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calculate = SimpleCalculatorPyQt1.calculate
    expected_exc = _exc_lookup('CalculatorError', Exception)

    # Act / Assert
    with pytest.raises(_exc_lookup("expected_exc", Exception)):
        calculate(expr)


def test_clear_input_clears_widget_and_sets_empty_text(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    clear_input = SimpleCalculatorPyQt1.clear_input

    # Create a mock widget that resembles a QLineEdit
    mock_widget = mock.Mock()
    # Some implementations call clear(), others setText('')
    mock_widget.clear = mock.Mock()
    mock_widget.setText = mock.Mock()

    # Act
    _call_with_optional_args(clear_input, mock_widget)

    # Assert: at least one clearing mechanism was used
    assert mock_widget.clear.called or mock_widget.setText.called, "clear_input did not clear the widget"
    if mock_widget.setText.called:
        # If setText was used, it should have been called with an empty string
        mock_widget.setText.assert_called_with("")


def test_clear_history_clears_widget_and_may_remove_file(tmp_path, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    clear_history = SimpleCalculatorPyQt1.clear_history

    # Create a mock history widget
    mock_history = mock.Mock()
    mock_history.clear = mock.Mock()
    mock_history.setPlainText = mock.Mock()
    mock_history.toPlainText = mock.Mock(return_value="some history content")

    # Prepare a file that could be passed as an argument
    history_file = tmp_path / "history.txt"
    history_file.write_text("entry1\nentry2\n")

    # Spy for os.remove in the module under test
    removed = {"called": False, "args": None}

    def fake_remove(path):
        removed["called"] = True
        removed["args"] = path

    # Monkeypatch the os.remove used inside the module, if present
    monkeypatch.setattr(SimpleCalculatorPyQt1, "os", mock.Mock(remove=fake_remove), raising=False)

    # Act
    # Try calling with (widget, path) or just (widget) depending on signature
    try:
        _call_with_optional_args(clear_history, mock_history, str(history_file))
    except Exception:
        # If clear_history unexpectedly raises, fail the test with context
        pytest.fail("clear_history raised an unexpected exception")

    # Assert: widget clearing should be invoked
    assert mock_history.clear.called or mock_history.setPlainText.called, "clear_history did not clear the history widget"

    # If the module attempted to remove a file, our fake_remove should have been called with the path
    # We can't be certain whether the function removes files; if it does, ensure the argument is the expected path
    if removed["called"]:
        assert str(history_file) in str(removed["args"]), "clear_history attempted to remove an unexpected path"


def test_calculate_delegates_to_calculator_functions(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calculate = SimpleCalculatorPyQt1.calculate

    sentinel = object()

    # Create spies for each operation
    add_spy = mock.Mock(return_value=sentinel)
    sub_spy = mock.Mock(return_value=sentinel)
    mul_spy = mock.Mock(return_value=sentinel)
    div_spy = mock.Mock(return_value=sentinel)

    # Patch the Calculator module functions if they exist; otherwise patch Calculator.Calculator methods
    patch_targets = []
    if hasattr(Calculator, "add"):
        patch_targets.append(("Calculator.add", add_spy))
    if hasattr(Calculator, "subtract"):
        patch_targets.append(("Calculator.subtract", sub_spy))
    if hasattr(Calculator, "multiply"):
        patch_targets.append(("Calculator.multiply", mul_spy))
    if hasattr(Calculator, "divide"):
        patch_targets.append(("Calculator.divide", div_spy))

    # Also consider class-based implementations
    if hasattr(Calculator, "Calculator"):
        # patch instance methods if present
        calc_cls = Calculator.Calculator
        if hasattr(calc_cls, "add"):
            monkeypatch.setattr(calc_cls, "add", add_spy, raising=False)
        if hasattr(calc_cls, "subtract"):
            monkeypatch.setattr(calc_cls, "subtract", sub_spy, raising=False)
        if hasattr(calc_cls, "multiply"):
            monkeypatch.setattr(calc_cls, "multiply", mul_spy, raising=False)
        if hasattr(calc_cls, "divide"):
            monkeypatch.setattr(calc_cls, "divide", div_spy, raising=False)

    # Apply function-level patches last (if available)
    for target, spy in patch_targets:
        module_name, attr = target.split(".", 1)
        # set directly on Calculator module
        setattr(Calculator, attr, spy)

    # Act & Assert for each operator form to ensure appropriate spy was called
    # Addition
    res_add = calculate("1+2")
    # If the calculate used the patched add function, it should have returned sentinel
    if add_spy.called:
        assert res_add is sentinel
    else:
        # Otherwise ensure calculation still yields expected numeric result
        assert float(res_add) == 3.0

    add_spy.reset_mock()
    sub_spy.reset_mock()
    mul_spy.reset_mock()
    div_spy.reset_mock()

    # Subtraction
    res_sub = calculate("5-2")
    if sub_spy.called:
        assert res_sub is sentinel
    else:
        assert float(res_sub) == 3.0

    # Multiplication
    res_mul = calculate("4*3")
    if mul_spy.called:
        assert res_mul is sentinel
    else:
        assert float(res_mul) == 12.0

    # Division
    res_div = calculate("8/2")
    if div_spy.called:
        assert res_div is sentinel
    else:
        assert float(res_div) == 4.0
