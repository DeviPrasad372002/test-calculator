import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import importlib
import inspect
import pytest

try:
    calc_mod = importlib.import_module("target.Calculator")
    Calculator = getattr(calc_mod, "Calculator", None)
    CalculatorError = getattr(calc_mod, "CalculatorError", None)
except Exception as exc:  # pragma: no cover - skip when target missing
    pytest.skip(f"target.Calculator not importable: {exc}", allow_module_level=True)

if Calculator is None:  # pragma: no cover - skip when class missing
    pytest.skip("target.Calculator.Calculator class not found", allow_module_level=True)

def _invoke_operation(op_name, a, b):
    # Try module-level function first (e.g., add(a,b))
    mod_func = getattr(calc_mod, op_name, None)
    if callable(mod_func):
        return mod_func(a, b)

    # Try class attribute (could be @staticmethod, @classmethod, or function descriptor)
    class_attr = getattr(Calculator, op_name, None)
    if callable(class_attr):
        # Try calling as static/class style (no instance)
        try:
            return class_attr(a, b)
        except TypeError:
            # Fall back to bound instance method
            pass

    # Try bound instance method
    try:
        instance = Calculator()
    except TypeError as exc:
        raise RuntimeError(f"Cannot instantiate Calculator without arguments: {exc}")

    bound = getattr(instance, op_name, None)
    if callable(bound):
        return bound(a, b)

    
    if callable(class_attr):
        return class_attr(instance, a, b)

    raise AttributeError(f"Operation {op_name} not found on module/class/instance")

def _expected_exceptions():
    basic = (TypeError, ValueError)
    if CalculatorError is not None:
        return (CalculatorError,) + basic
    return basic

def test___init___creates_instance_and_has_operations():
    
    # Arrange / Act
    try:
        instance = Calculator()
    except TypeError:
        pytest.skip("Calculator.__init__ requires parameters; skipping instantiation-specific test")

    # Assert
    assert isinstance(instance, Calculator), "Instance should be of Calculator type"
    assert callable(getattr(instance, "add", None)), "Instance should have callable 'add'"
    assert callable(getattr(instance, "subtract", None)), "Instance should have callable 'subtract'"

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (1, 2, 3),
        (0, 0, 0),
        (-1, 5, 4),
    ],
)
def test_add_integers_returns_expected_sum(a, b, expected):
    
    # Arrange / Act
    result = _invoke_operation("add", a, b)

    # Assert
    assert result == expected
    assert isinstance(result, (int, float)), "Result of integer addition should be numeric"

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (5.5, 2.2, 3.3),
        (-1.0, -2.5, 1.5),
        (10.0, 0.0, 10.0),
    ],
)
def test_subtract_floats_and_negatives_return_correct_value(a, b, expected):
    
    # Arrange / Act
    result = _invoke_operation("subtract", a, b)

    # Assert: allow for typical floating point rounding
    assert isinstance(result, (int, float)), "Result should be numeric"
    assert pytest.approx(expected, rel=1e-9) == result

def test_add_invalid_types_raises_expected_exception():
    
    # Arrange
    bad_a = "not-a-number"
    bad_b = 2

    # Act / Assert
    expected = _expected_exceptions()
    with pytest.raises(expected):
        _invoke_operation("add", bad_a, bad_b)
