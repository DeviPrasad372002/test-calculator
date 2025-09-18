import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import inspect
import pytest

try:
    from target.Calculator import Calculator, CalculatorError
except Exception:
    pytest.skip("target.Calculator module not available", allow_module_level=True)

def _call_bound_method(instance, name, *args, **kwargs):
    # Helper: prefer bound method on instance; fall back to attribute on class if missing
    if hasattr(instance, name):
        return getattr(instance, name)(*args, **kwargs)
    cls = instance.__class__
    if hasattr(cls, name):
        func = getattr(cls, name)
        # try calling as a function; if it requires self, provide instance
        try:
            return func(*args, **kwargs)
        except TypeError:
            return func(instance, *args, **kwargs)
    raise AttributeError(f"{name} not found on instance or class")

def test_Calculator_init_no_args_creates_instance_and_exposes_methods():
    
    # Arrange / Act
    inst = Calculator()
    # Assert
    assert isinstance(inst, Calculator)
    assert hasattr(inst, "add") and callable(getattr(inst, "add"))
    assert hasattr(inst, "subtract") and callable(getattr(inst, "subtract"))

def test_Calculator_init_accepts_single_positional_if_supported():
    
    # Arrange
    sig = inspect.signature(Calculator.__init__)
    params = list(sig.parameters.values())[1:]  # exclude 'self'
    # Act / Assert: attempt to construct with a single numeric arg if constructor accepts at least one param
    if not params:
        pytest.skip("Calculator.__init__ takes no extra positional parameters; skipping variant-construction test")
    try:
        inst = Calculator(10)
    except TypeError:
        pytest.skip("Calculator.__init__ does not accept a single positional argument (10)")
    # Assert
    assert isinstance(inst, Calculator)

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (2, 3, 5),
        (-1, 5, 4),
        (1.5, 2.25, 3.75),
    ],
)
def test_Calculator_add_various_numeric_inputs_return_expected(a, b, expected):
    
    # Arrange
    inst = Calculator()
    # Act
    result = _call_bound_method(inst, "add", a, b)
    # Assert
    if isinstance(expected, float):
        assert pytest.approx(expected) == result
    else:
        assert result == expected
        assert type(result) is type(expected)

@pytest.mark.parametrize("a,b", [("x", 1), (None, 2), ("a", "b")])
def test_Calculator_add_invalid_raises_calculator_error(a, b):
    
    # Arrange
    inst = Calculator()
    # Act / Assert
    with pytest.raises(CalculatorError):
        _call_bound_method(inst, "add", a, b)

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (5, 3, 2),
        (0, 0, 0),
        (2.5, 1.25, 1.25),
    ],
)
def test_Calculator_subtract_various_numeric_inputs_return_expected(a, b, expected):
    
    # Arrange
    inst = Calculator()
    # Act
    result = _call_bound_method(inst, "subtract", a, b)
    # Assert
    if isinstance(expected, float):
        assert pytest.approx(expected) == result
    else:
        assert result == expected
        assert type(result) is type(expected)
