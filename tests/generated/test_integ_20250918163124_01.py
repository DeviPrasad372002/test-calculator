import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import pytest
from unittest import mock

try:
    from target import Calculator as calc_module
except ImportError:
    pytest.skip("target.Calculator module not available; skipping integration tests", allow_module_level=True)

@pytest.mark.parametrize("a,b,expected", [
    (2, 3, 5),
    (0, 0, 0),
    (-1, 1, 0),
    (2.5, 0.5, 3.0),
])
def test_add_and_subtract_module_level_basic(a, b, expected):
    
    # Arrange
    assert hasattr(calc_module, "add"), "Module is missing 'add' function"
    assert hasattr(calc_module, "subtract"), "Module is missing 'subtract' function"

    add_fn = getattr(calc_module, "add")
    subtract_fn = getattr(calc_module, "subtract")

    # Act
    result_add = add_fn(a, b)
    result_sub = subtract_fn(expected, b)

    # Assert
    assert result_add == expected
    assert isinstance(result_add, (int, float))
    assert result_sub == a
    assert isinstance(result_sub, (int, float))

def test_Calculator_instance_methods_cross_module(monkeypatch):
    
    # Arrange
    assert hasattr(calc_module, "Calculator"), "Module is missing 'Calculator' class"
    Calculator = getattr(calc_module, "Calculator")
    # Prevent any accidental external calls on construction if present
    # If the module exposes an external_service attribute used by Calculator, mock it
    if hasattr(calc_module, "external_service"):
        monkeypatch.setattr(calc_module, "external_service", mock.Mock(return_value=None))

    inst = Calculator()

    # Prefer instance methods but fall back to module-level functions for integration
    add_callable = getattr(inst, "add", None) or getattr(calc_module, "add", None)
    subtract_callable = getattr(inst, "subtract", None) or getattr(calc_module, "subtract", None)

    assert callable(add_callable), "No callable add available on instance or module"
    assert callable(subtract_callable), "No callable subtract available on instance or module"

    # Act
    sum_result = add_callable(7, 8)
    diff_result = subtract_callable(10, 4)

    # Assert
    assert sum_result == 15
    assert isinstance(sum_result, (int, float))
    assert diff_result == 6
    assert isinstance(diff_result, (int, float))

@pytest.mark.parametrize("caller_name", ["module_divide", "instance_divide"])
def test_divide_by_zero_raises_CalculatorError(caller_name):
    
    # Arrange
    assert hasattr(calc_module, "CalculatorError"), "Module is missing 'CalculatorError' exception class"
    CalculatorError = getattr(calc_module, "CalculatorError")

    # Prepare two possible callers: module-level divide or instance method
    callers = {}
    if hasattr(calc_module, "divide"):
        callers["module_divide"] = getattr(calc_module, "divide")
    if hasattr(calc_module, "Calculator"):
        inst = getattr(calc_module, "Calculator")()
        if hasattr(inst, "divide"):
            callers["instance_divide"] = getattr(inst, "divide")

    if caller_name not in callers:
        pytest.skip(f"{caller_name} not available in module; skipping this variant")

    divide_callable = callers[caller_name]

    # Act / Assert
    with pytest.raises(CalculatorError):
        divide_callable(1, 0)
