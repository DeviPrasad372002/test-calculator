import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import pytest

# Guard third-party imports that the target module may rely on
try:
    import PyQt5  
except Exception:
    pytest.skip("PyQt5 not available, skipping tests that rely on target.Calculator", allow_module_level=True)

# Import the unit under test
try:
    from target.Calculator import Calculator, CalculatorError, multiply, divide
except Exception:
    pytest.skip("target.Calculator module or expected attributes not available", allow_module_level=True)

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (3, 4, 12),
        (0, 5, 0),
        (-2, 6, -12),
        (2.5, 4, 10.0),
    ],
)
def test_multiply_various_numeric_inputs(a, b, expected):
    
    # Arrange: inputs provided by parametrize
    # Act
    result = multiply(a, b)
    # Assert: concrete value and type
    assert result == expected
    # If expected is int, ensure type is int when operands are ints
    if all(isinstance(x, int) for x in (a, b)):
        assert isinstance(result, int)

def test_multiply_with_large_numbers_does_not_overflow():
    
    # Arrange
    a = 10**6
    b = 10**6
    # Act
    result = multiply(a, b)
    # Assert: correct arithmetic without overflow (Python ints are arbitrary precision)
    assert result == 10**12
    assert isinstance(result, int)

def test_divide_normal_and_fractional_result():
    
    # Arrange
    numerator = 7
    denominator = 2
    # Act
    result = divide(numerator, denominator)
    # Assert: exact division expected (float)
    assert result == 3.5
    assert isinstance(result, float)

def test_divide_by_zero_raises_calculator_error():
    
    # Arrange
    numerator = 1
    denominator = 0
    # Act / Assert
    with pytest.raises(CalculatorError):
        divide(numerator, denominator)

def test_calculator_instance_methods_match_module_functions():
    
    # Arrange
    calc = Calculator()
    inputs = [
        (3, 5),
        (0, 9),
        (-4, 2),
        (2.5, 4),
    ]
    # Act / Assert
    for a, b in inputs:
        # multiply
        assert calc.multiply(a, b) == multiply(a, b)
        # divide (skip divide-by-zero case)
        if b != 0:
            assert calc.divide(a, b) == divide(a, b)
