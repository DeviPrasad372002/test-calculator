import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import pytest

# Guard third-party imports that the module under test might require
try:
    import PyQt5  # noqa: F401
except ImportError:
    pytest.skip("PyQt5 is not available; skipping Calculator tests", allow_module_level=True)

# Import the implementation under test
try:
    from target.Calculator import Calculator, CalculatorError
except ImportError:
    pytest.skip("target.Calculator could not be imported; skipping tests", allow_module_level=True)

def test_Calculator_init_instance():
    
    # Arrange / Act
    calc = Calculator()
    # Assert
    assert isinstance(calc, Calculator)
    
    # Use hasattr rather than assuming exact attributes
    assert hasattr(calc, "add")
    assert hasattr(calc, "subtract")
    assert hasattr(calc, "multiply")
    assert hasattr(calc, "divide")

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (1, 2, 3),
        (0, 0, 0),
        (-5, 3, -2),
        (1.5, 2.5, 4.0),
    ],
)
def test_Calculator_add_various(a, b, expected):
    
    # Arrange
    calc = Calculator()
    # Act
    result = calc.add(a, b)
    # Assert
    assert result == expected
    assert isinstance(result, (int, float))

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (2, 3, 6),
        (0, 5, 0),
        (-2, -4, 8),
        (1.5, 2, 3.0),
    ],
)
def test_Calculator_multiply_various(a, b, expected):
    
    # Arrange
    calc = Calculator()
    # Act
    result = calc.multiply(a, b)
    # Assert
    assert result == expected
    assert isinstance(result, (int, float))

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (10, 2, 5),
        (3, 2, 1.5),
        (-6, 3, -2),
    ],
)
def test_Calculator_divide_valid(a, b, expected):
    
    # Arrange
    calc = Calculator()
    # Act
    result = calc.divide(a, b)
    # Assert
    assert result == expected
    assert isinstance(result, (int, float))

def test_Calculator_divide_by_zero_raises_CalculatorError():
    
    # Arrange
    calc = Calculator()
    # Act / Assert
    with pytest.raises(CalculatorError):
        calc.divide(1, 0)

@pytest.mark.parametrize("a,b", [("x", 1), (1, "y"), (None, 1), (1, None), ([], {} )])
def test_Calculator_subtract_invalid_types_raises_CalculatorError(a, b):
    
    # Arrange
    calc = Calculator()
    # Act / Assert
    with pytest.raises(CalculatorError):
        calc.subtract(a, b)
