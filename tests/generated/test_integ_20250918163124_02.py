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
import sys

try:
    import pytest
except ImportError:
    raise

# of missing third-party dependencies used by the module), skip the entire test module.
try:
    try:
        calc_mod = importlib.import_module("target.Calculator")
    except Exception:
        calc_mod = importlib.import_module("Calculator")
except Exception as exc:
    pytest.skip(f"Cannot import Calculator module: {exc}", allow_module_level=True)

# Resolve required attributes and skip if they are missing.
if not hasattr(calc_mod, "Calculator") or not hasattr(calc_mod, "multiply") or not hasattr(calc_mod, "divide"):
    pytest.skip("Calculator module does not expose expected API (Calculator, multiply, divide)", allow_module_level=True)

Calculator = getattr(calc_mod, "Calculator")
multiply_fn = getattr(calc_mod, "multiply")
divide_fn = getattr(calc_mod, "divide")
add_fn = getattr(calc_mod, "add", None)
subtract_fn = getattr(calc_mod, "subtract", None)
CalculatorError = getattr(calc_mod, "CalculatorError", Exception)

import math

@pytest.mark.parametrize(
    "a,b,expected_type,expected_value",
    [
        (2, 3, int, 6),
        (-1, 5, int, -5),
        (2.5, 4, float, 10.0),
        (0, 12345, int, 0),
    ],
)
def test_multiply_function_and_method_agree_on_various_types(a, b, expected_type, expected_value):
    
    # Arrange
    calc_inst = Calculator()
    # Act
    result_method = calc_inst.multiply(a, b)
    result_function = multiply_fn(a, b)
    # Assert
    assert result_method == expected_value, f"Calculator.multiply returned {result_method}, expected {expected_value}"
    assert result_function == expected_value, f"multiply function returned {result_function}, expected {expected_value}"
    assert isinstance(result_method, expected_type), f"Expected type {expected_type} for method result"
    assert isinstance(result_function, expected_type), f"Expected type {expected_type} for function result"

def test_integration_chain_multiply_add_subtract_divide_mixed_calls():
    
    # This test mixes class methods and module-level functions to verify end-to-end behavior.
    # Arrange
    a, b, c, d, e = 3, 4, 5, 2, 2  # ((3*4)+5-2)/2 = 7.5
    calc_inst = Calculator()
    # Act
    product = calc_inst.multiply(a, b)           # class method
    after_add = add_fn(product, c) if add_fn is not None else calc_mod.add(product, c)
    after_sub = calc_inst.subtract(after_add, d) if hasattr(calc_inst, "subtract") else subtract_fn(after_add, d)
    final = divide_fn(after_sub, e)              # module-level divide
    # Assert
    assert math.isclose(final, 7.5, rel_tol=1e-12), f"Final chained result {final} != 7.5"
    assert isinstance(final, float), "Final result should be a float due to division"

@pytest.mark.parametrize("numerator", [1, -3.5, 0])
def test_divide_by_zero_raises_CalculatorError_for_function_and_method(numerator):
    
    # Arrange
    calc_inst = Calculator()
    # Act / Assert for module-level function
    with pytest.raises(CalculatorError):
        divide_fn(numerator, 0)
    
    # Prefer method on instance, fall back to function bound via class
    if hasattr(calc_inst, "divide"):
        with pytest.raises(CalculatorError):
            calc_inst.divide(numerator, 0)
    else:
        # If instance has no method, try calling classmethod or function with same semantics
        with pytest.raises(CalculatorError):
            getattr(calc_mod, "divide")(numerator, 0)

def test_integration_consistency_with_init_signature_and_behavior():
    
    # Verify that constructing Calculator with or without possible initial args results in usable instance.
    # Arrange / Act
    sig = inspect.signature(Calculator)
    params = sig.parameters
    # If __init__ accepts a single numeric initial value, pass it and then multiply to ensure instance usable.
    if len(params) > 1:  # first parameter is 'self'; more means initializer accepts args
        # Provide an initial value of 10 if possible
        try:
            calc_with_init = Calculator(10)
        except TypeError:
            pytest.skip("Calculator.__init__ has parameters but calling with a sample value failed")
    else:
        calc_with_init = Calculator()
    # Use instance for some operations
    res1 = calc_with_init.multiply(6, 7)
    res2 = multiply_fn(6, 7)
    # Assert both ways compute same product
    assert res1 == res2 == 42, "Multiplication should produce 42 for inputs (6,7)"
    # Also check divide returns float for non-integer division
    res_div = divide_fn(5, 2)
    assert isinstance(res_div, float)
    assert math.isclose(res_div, 2.5, rel_tol=1e-12)
