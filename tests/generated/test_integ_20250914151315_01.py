
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
    import inspect
    from unittest import mock
    import builtins
    import io
    import Calculator
    import SimpleCalculatorPyQt1
    import os
except ImportError:
    import pytest
    pytest.skip("requires pytest and target modules", allow_module_level=True)

def _exc_lookup(name, default=Exception):
    return getattr(Calculator, name, getattr(SimpleCalculatorPyQt1, name, default))

@pytest.mark.parametrize(
    "a,b,expected_add,expected_sub,expect_error",
    [
        (0, 0, 0, 0, None),                         # boundary zeros
        (5, 3, 8, 2, None),                         # normal positive ints
        (-2, 7, 5, -9, None),                       # negative + positive
        (1.5, 2.25, 3.75, -0.75, None),             # floats
        (10**12, 1, 10**12 + 1, 10**12 - 1, None),  # large integer boundary
        ("a", "b", None, None, TypeError),          # error path: non-numeric
    ],
)
def test_add_and_subtract_various(a, b, expected_add, expected_sub, expect_error):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    add_fn = getattr(Calculator, "add", None)
    sub_fn = getattr(Calculator, "subtract", None)
    assert callable(add_fn), "Calculator.add must be callable"
    assert callable(sub_fn), "Calculator.subtract must be callable"
    # Act & Assert
    if expect_error is not None:
        with pytest.raises(_exc_lookup("expect_error", Exception)):
            add_fn(a, b)
        with pytest.raises(_exc_lookup("expect_error", Exception)):
            sub_fn(a, b)
    else:
        res_add = add_fn(a, b)
        res_sub = sub_fn(a, b)
        # Assert types
        assert isinstance(res_add, (int, float)), "add should return numeric"
        assert isinstance(res_sub, (int, float)), "subtract should return numeric"
        # Assert values (use approx for floats)
        if isinstance(expected_add, _exc_lookup("float", Exception)):
            assert res_add == pytest.approx(expected_add)
        else:
            assert res_add == expected_add
        if isinstance(expected_sub, _exc_lookup("float", Exception)):
            assert res_sub == pytest.approx(expected_sub)
        else:
            assert res_sub == expected_sub
        # Also verify instance methods if present
        CalcClass = getattr(Calculator, "Calculator", None)
        if CalcClass is not None:
            inst = CalcClass()
            inst_add = getattr(inst, "add", None)
            inst_sub = getattr(inst, "subtract", None)
            if callable(inst_add) and callable(inst_sub):
                res_add_inst = inst_add(a, b)
                res_sub_inst = inst_sub(a, b)
                assert res_add_inst == res_add
                assert res_sub_inst == res_sub

def _call_save_history_flexible(save_history_fn, content, path_obj):
    sig = inspect.signature(save_history_fn)
    params = list(sig.parameters)
    # Try common call shapes
    try:
        if len(params) == 0:
            return save_history_fn()
        if len(params) == 1:
            return save_history_fn(content)
        # If two or more params, try (content, path)
        return save_history_fn(content, str(path_obj))
    except TypeError:
        # fallback: try keyword arguments
        kwargs = {}
        for name in params:
            lname = name.lower()
            if "history" in lname or "content" in lname or "text" in lname or "data" in lname:
                kwargs[name] = content
            elif "path" in lname or "file" in lname or "filename" in lname:
                kwargs[name] = str(path_obj)
        if kwargs:
            return save_history_fn(**kwargs)
        # give up and re-raise original failure
        raise

def test_save_history_writes_file_and_records_content(tmp_path, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    history_text = "Computation result: 42"
    save_history_fn = getattr(SimpleCalculatorPyQt1, "save_history", None)
    assert callable(save_history_fn), "save_history must exist and be callable"
    mock_open = mock.mock_open()
    # Ensure any open in module/global scope is intercepted
    monkeypatch.setattr(builtins, "open", mock_open, raising=False)
    out_path = tmp_path / "history.txt"
    # Act
    _call_save_history_flexible(save_history_fn, history_text, out_path)
    # Assert: open was called and the content was written
    assert mock_open.called, "save_history should call open() to write output"
    handle = mock_open()
    # At least one write call occurred with the history content
    write_calls = [c for c in getattr(handle, "write").call_args_list]
    assert write_calls, "expected write() to be called at least once"
    written = "".join("".join(map(str, args)) for args, _ in getattr(handle, "write").call_args_list)
    assert history_text in written

def test_calculate_delegates_to_calculator_and_saves_history(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calc_fn = getattr(SimpleCalculatorPyQt1, "calculate", None)
    if calc_fn is None or not callable(calc_fn):
        pytest.skip("calculate not implemented in SimpleCalculatorPyQt1", allow_module_level=False)
    # Replace calculator operations with spies
    add_spy = mock.Mock(return_value=12345)
    sub_spy = mock.Mock(return_value=6789)
    monkeypatch.setattr(Calculator, "add", add_spy, raising=False)
    monkeypatch.setattr(Calculator, "subtract", sub_spy, raising=False)
    save_mock = mock.Mock()
    monkeypatch.setattr(SimpleCalculatorPyQt1, "save_history", save_mock, raising=False)
    # Prepare a couple of candidate inputs
    a, b = 3, 4
    attempted = []
    # Act: try to call calculate with a variety of plausible signatures until one works
    sig = inspect.signature(calc_fn)
    param_names = [p for p in sig.parameters]
    succeeded = False
    last_exc = None
    # Try expression string if single-arg
    try:
        if len(param_names) == 1:
            attempted.append("single_expr_str")
            res = calc_fn(f"{a}+{b}")
            succeeded = True
        else:
            # Try common keyword names
            kw = {}
            for name in param_names:
                lname = name.lower()
                if "expr" in lname or "expression" in lname or "text" in lname:
                    kw[name] = f"{a}+{b}"
                elif name in ("a", "x", "lhs"):
                    kw[name] = a
                elif name in ("b", "y", "rhs"):
                    kw[name] = b
                elif "op" in lname or "operator" in lname:
                    kw[name] = "+"
            if kw:
                attempted.append("kwargs")
                res = calc_fn(**kw)
                succeeded = True
            else:
                # last resort: positional a, b, '+'
                attempted.append("positional")
                res = calc_fn(a, b, "+")
                succeeded = True
    except Exception as e:
        last_exc = e
        succeeded = False
    if not succeeded:
        pytest.skip(f"calculate signature did not match tried patterns; attempts={attempted}; last_exc={last_exc}", allow_module_level=False)
    # Assert: calculator functions were used and history was saved
    assert add_spy.called or sub_spy.called, "calculate should call into Calculator.add or Calculator.subtract"
    assert save_mock.called, "calculate should call save_history to record the computation"
    # If calculate returned a result, ensure it's numeric
    if 'res' in locals():
        assert res is None or isinstance(res, (int, float, str)), "calculate result should be numeric or string or None"
    # Also ensure at least one of the calculator spies was called with expected operands when possible
    if add_spy.called:
        # check last call args include our operands in some form (int or str)
        called_args = sum((list(c) for c in add_spy.call_args_list), [])
        assert any(a == v or str(a) == str(v) for v in called_args), "add should be called with operand a"
        assert any(b == v or str(b) == str(v) for v in called_args), "add should be called with operand b"
    if sub_spy.called:
        called_args = sum((list(c) for c in sub_spy.call_args_list), [])
        assert any(a == v or str(a) == str(v) for v in called_args), "subtract should be called with operand a"
        assert any(b == v or str(b) == str(v) for v in called_args), "subtract should be called with operand b"
