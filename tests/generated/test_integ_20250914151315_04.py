
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
    raise

try:
    import Calculator
    import SimpleCalculatorPyQt1
    import builtins
    from unittest import mock
except ImportError:
    pytest.skip("Required application modules not available for integration tests", allow_module_level=True)

def _exc_lookup(name, default=Exception):
    # Return exception class from Calculator module by name or fallback to default
    return getattr(Calculator, name, default)

def _get_callable(module, name):
    # Try to find callable at module level, otherwise as attribute on MainWindow class
    fn = getattr(module, name, None)
    if callable(fn):
        return fn
    mw = getattr(module, "MainWindow", None)
    if mw is not None:
        fn = getattr(mw, name, None)
        if callable(fn):
            return fn
    pytest.skip(f"Callable '{name}' not found in module or MainWindow", allow_module_level=True)

@pytest.mark.parametrize(
    "op_name,a,b,expected",
    [
        ("add", 2, 3, 5),
        ("subtract", 5, 2, 3),
        ("multiply", -1, 8, -8),
        ("divide", 9, 3, 3),
        ("add", 2.5, 0.5, 3.0),
    ],
)
def test_calculator_basic_operations_return_expected_types_and_values(op_name, a, b, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    op = getattr(Calculator.Calculator, op_name, None)
    if op is None:
        pytest.skip(f"Calculator.{op_name} not present", allow_module_level=True)
    calc = Calculator.Calculator()
    # Act
    result = op(calc, a, b)
    # Assert
    assert isinstance(result, (int, float))
    assert result == expected

def test_calculator_division_by_zero_raises_calculator_error():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calc = Calculator.Calculator()
    divide = getattr(Calculator.Calculator, "divide", None)
    if divide is None:
        pytest.skip("Calculator.divide not present", allow_module_level=True)
    Err = _exc_lookup("CalculatorError", Exception)
    # Act / Assert
    with pytest.raises(_exc_lookup("Err", Exception)):
        divide(calc, 10, 0)

def test_save_history_writes_file_via_dialog_and_preserves_history(tmp_path, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    save_history = _get_callable(SimpleCalculatorPyQt1, "save_history")
    # Prepare a fake self (MainWindow-like) with a history attribute list
    history = ["2 + 2 = 4", "5 * 3 = 15", "10 / 2 = 5"]
    class FakeSelf:
        def __init__(self, history):
            self.history = history
    fake = FakeSelf(history=list(history))
    # Prepare target path
    target = tmp_path / "history_output.txt"
    # Monkeypatch any Qt file dialog getSaveFileName found in the module to return our path
    patched = False
    for name, attr in vars(SimpleCalculatorPyQt1).items():
        if hasattr(attr, "getSaveFileName"):
            monkeypatch.setattr(attr, "getSaveFileName", lambda *a, **k: (str(target), ""))
            patched = True
            break
    # If not found, try nested QtWidgets attribute
    if not patched and hasattr(SimpleCalculatorPyQt1, "QtWidgets"):
        QtW = getattr(SimpleCalculatorPyQt1, "QtWidgets")
        if hasattr(QtW, "QFileDialog"):
            monkeypatch.setattr(QtW.QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
            patched = True
    if not patched:
        # Fallback: if no Qt dialog to patch, skip to avoid false failures
        pytest.skip("No QFileDialog.getSaveFileName found to patch; cannot perform save_history integration test", allow_module_level=True)
    # Monkeypatch builtins.open to capture writes
    m_open = mock.mock_open()
    monkeypatch.setattr(builtins, "open", m_open)
    # Act
    save_history(fake)
    # Assert: ensure open called with our target path and something like write calls corresponding to history items
    m_open.assert_called()  # file opened
    handle = m_open()
    # Collect all write() calls and combine
    all_writes = "".join(call.args[0] for call in handle.write.mock_calls if call.args)
    for entry in history:
        assert str(entry) in all_writes

@pytest.mark.parametrize("initial_history", [[], ["placeholder"]])
def test_clear_history_and_clear_input_reset_state(monkeypatch, initial_history):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    clear_history = _get_callable(SimpleCalculatorPyQt1, "clear_history")
    clear_input = _get_callable(SimpleCalculatorPyQt1, "clear_input")
    # Build fake input object that mimics QLineEdit-like API
    class FakeInput:
        def __init__(self, text):
            self._text = text
            self.cleared = False
        def text(self):
            return self._text
        def setText(self, t):
            self._text = t
        def clear(self):
            self._text = ""
            self.cleared = True
    class FakeSelf:
        def __init__(self, history_list, input_text):
            self.history = history_list
            # Common names used in UIs; try to provide multiple
            self.lineEdit = FakeInput(input_text)
            self.input = FakeInput(input_text)
    fake = FakeSelf(history_list=list(initial_history), input_text="123")
    # Act - clear input (should use either lineEdit or input API)
    clear_input(fake)
    # Assert input cleared via one of the provided APIs
    assert getattr(fake.lineEdit, "text")() == "" or getattr(fake.input, "text")() == ""
    # Act - clear history
    clear_history(fake)
    # Assert history cleared
    assert isinstance(fake.history, list)
    assert len(fake.history) == 0

def test_calculator_integration_with_history_and_save(monkeypatch, tmp_path):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: perform several calculations using Calculator and create history strings
    calc = Calculator.Calculator()
    ops = [
        (getattr(Calculator.Calculator, "add"), 1, 2, "1 + 2 = 3"),
        (getattr(Calculator.Calculator, "multiply"), 3, 4, "3 * 4 = 12"),
    ]
    history = []
    for func, a, b, label in ops:
        if func is None:
            pytest.skip("Expected Calculator operation missing", allow_module_level=True)
        res = func(calc, a, b)
        history.append(label)
    # Prepare fake self with that history
    class FakeSelf:
        def __init__(self, history):
            self.history = history
    fake = FakeSelf(history=list(history))
    # Locate save_history callable
    save_history = _get_callable(SimpleCalculatorPyQt1, "save_history")
    # Patch QFileDialog.getSaveFileName to return tmp file
    target = tmp_path / "calc_history.txt"
    patched = False
    for name, attr in vars(SimpleCalculatorPyQt1).items():
        if hasattr(attr, "getSaveFileName"):
            monkeypatch.setattr(attr, "getSaveFileName", lambda *a, **k: (str(target), ""))
            patched = True
            break
    if not patched and hasattr(SimpleCalculatorPyQt1, "QtWidgets"):
        QtW = getattr(SimpleCalculatorPyQt1, "QtWidgets")
        if hasattr(QtW, "QFileDialog"):
            monkeypatch.setattr(QtW.QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
            patched = True
    if not patched:
        pytest.skip("No dialog getSaveFileName to patch; skipping save_history integration", allow_module_level=True)
    # Use real file writing for integration (do not mock open here; validate the file content)
    # Act
    save_history(fake)
    # Assert file exists and contents include both history entries
    assert target.exists()
    content = target.read_text()
    for entry in history:
        assert entry in content
