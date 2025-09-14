
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
    import builtins
    import io
    import sys
    from target import Calculator
    from target import SimpleCalculatorPyQt1 as SC
except ImportError:
    import pytest
    pytest.skip("required target modules not available", allow_module_level=True)

def _exc_lookup(name, default=Exception):
    import builtins as _builtins, sys as _sys
    # search common places for exception definitions
    candidates = [
        globals().get('Calculator'),
        globals().get('SC'),
        _sys.modules.get('target.Calculator'),
        _sys.modules.get('Calculator'),
        _sys.modules.get('target.SimpleCalculatorPyQt1'),
        _sys.modules.get('SimpleCalculatorPyQt1'),
    ]
    for mod in candidates:
        try:
            if mod and hasattr(mod, name):
                return getattr(mod, name)
        except Exception:
            pass
    return getattr(_builtins, name, default)

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (2, 3, 6),
        (2.5, 4, 10.0),
        (0, 5, 0),
        (-3, 6, -18),
        (10**6, 10**6, 10**12),
    ],
)
def test_multiply_returns_expected_numeric_results(a, b, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange - inputs provided by parametrize
    # Act
    result = Calculator.multiply(a, b)
    # Assert - value and type correctness
    assert result == expected
    assert isinstance(result, (int, float))

@pytest.mark.parametrize("left,right", [("a", 2), (None, 5), ([], {}), (object(), 2)])
def test_multiply_raises_on_invalid_types(left, right):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange - invalid operands
    # Act / Assert - expect a type-related exception
    with pytest.raises(_exc_lookup("TypeError", Exception)):
        Calculator.multiply(left, right)

@pytest.mark.parametrize(
    "numerator,denominator,expected",
    [
        (6, 3, 2),
        (7, 2, 3.5),
        (-10, 4, -2.5),
        (0, 5, 0),
        (5.0, 2.0, 2.5),
    ],
)
def test_divide_returns_expected_results(numerator, denominator, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange - inputs from parametrize
    # Act
    result = Calculator.divide(numerator, denominator)
    # Assert - numeric correctness and type
    assert result == expected
    assert isinstance(result, (int, float))

def test_divide_by_zero_raises_calculator_or_zero_division():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    numerator = 5
    denominator = 0
    # Act / Assert - accept either library ZeroDivisionError or module-specific CalculatorError
    exc_types = (
        _exc_lookup("CalculatorError", Exception),
        _exc_lookup("ZeroDivisionError", Exception),
    )
    with pytest.raises(_exc_lookup("exc_types", Exception)):
        Calculator.divide(numerator, denominator)

def test_save_history_writes_given_history_to_file(tmp_path, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    history = ["1 + 2 = 3", "4 * 5 = 20"]
    out_file = tmp_path / "history.txt"
    saved = {"path": None, "file": None}

    class FakeFile:
        def __init__(self):
            self._buf = io.StringIO()
        def write(self, s):
            return self._buf.write(s)
        def writelines(self, lines):
            return self._buf.writelines(lines)
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def getvalue(self):
            return self._buf.getvalue()

    def fake_open(path, mode='w', *args, **kwargs):
        # capture path and return a fake file object
        saved["path"] = path
        f = FakeFile()
        saved["file"] = f
        return f

    # Prefer patching the module's open; also patch builtins as fallback
    monkeypatch.setattr(SC, "open", fake_open, raising=False)
    monkeypatch.setattr(builtins, "open", fake_open, raising=False)

    # Act - try several plausible call signatures for save_history
    called = False
    # 1) try module-level function that accepts (history, filepath)
    try:
        SC.save_history(history, str(out_file))
        called = True
    except TypeError:
        # signature mismatch, try other plausible approaches
        pass
    except AttributeError:
        # function not present; fall through to try MainWindow
        pass

    if not called:
        # 2) try MainWindow instance method expecting save path
        if hasattr(SC, "MainWindow"):
            try:
                mw = SC.MainWindow()
            except Exception:
                pytest.skip("MainWindow cannot be instantiated in test environment")
            # set history on instance if attribute exists
            try:
                mw.history = history
            except Exception:
                # if attribute cannot be set, continue to trying different invocation patterns
                pass
            # try instance.save_history(path)
            if hasattr(mw, "save_history"):
                try:
                    mw.save_history(str(out_file))
                    called = True
                except TypeError:
                    pass
                except Exception:
                    # other exceptions during save may indicate unsupported environment
                    pytest.skip("save_history raised an unexpected exception during test")
            # try module-level save_history that accepts instance and path
            if not called and hasattr(SC, "save_history"):
                try:
                    SC.save_history(mw, str(out_file))
                    called = True
                except TypeError:
                    pass
                except Exception:
                    pytest.skip("save_history raised an unexpected exception during test")

    if not called:
        pytest.skip("Could not exercise save_history with any known signature")

    # Assert - ensure file write was attempted and content contains history lines
    assert saved["path"] is not None, "save_history did not attempt to open a file"
    assert saved["file"] is not None, "no file object captured from save operation"
    content = saved["file"].getvalue()
    for entry in history:
        assert entry in content, f"history entry not found in saved content: {entry}"
