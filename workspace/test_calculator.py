import unittest
from calculator import Calculator

class TestCalculator(unittest.TestCase):
    
    def setUp(self):
        """Set up a fresh Calculator instance before each test."""
        self.calc = Calculator()

    # --- Test Addition (+)
    def test_add_positive_numbers(self):
        self.assertEqual(self.calc.add(5, 3), 8)

    def test_add_negative_numbers(self):
        self.assertEqual(self.calc.add(-5, -3), -8)

    def test_add_mixed_numbers(self):
        self.assertEqual(self.calc.add(10, -5), 5)

    def test_add_with_zero(self):
        self.assertEqual(self.calc.add(7, 0), 7)

    # --- Test Subtraction (-)
    def test_subtract_positive_numbers(self):
        self.assertEqual(self.calc.subtract(10, 5), 5)

    def test_subtract_negative_result(self):
        self.assertEqual(self.calc.subtract(5, 10), -5)

    def test_subtract_with_negative_inputs(self):
        self.assertEqual(self.calc.subtract(-5, -3), -2)

    # --- Test Multiplication (*)
    def test_multiply_positive_numbers(self):
        self.assertEqual(self.calc.multiply(4, 5), 20)

    def test_multiply_by_zero(self):
        self.assertEqual(self.calc.multiply(100, 0), 0)

    def test_multiply_by_negative(self):
        self.assertEqual(self.calc.multiply(4, -5), -20)

    # --- Test Division (/)
    def test_divide_positive_numbers(self):
        self.assertEqual(self.calc.divide(10, 2), 5.0)

    def test_divide_by_one(self):
        self.assertEqual(self.calc.divide(5, 1), 5.0)

    def test_divide_by_negative(self):
        self.assertEqual(self.calc.divide(10, -2), -5.0)

    def test_divide_with_floats(self):
        # Use assertAlmostEqual for floating point comparisons
        self.assertAlmostEqual(self.calc.divide(7, 2), 3.5)

    # --- Edge Case Testing
    
    def test_division_by_zero(self):
        """Test division by zero, expecting ZeroDivisionError."""
        with self.assertRaises(ZeroDivisionError):
            self.calc.divide(10, 0)

    def test_non_numeric_input(self):
        """Test handling of non-numeric inputs (assuming the calculator handles type errors)."""
        # Assuming the calculator raises TypeError for invalid input types
        with self.assertRaises(TypeError):
            self.calc.add(10, "a")

    def test_all_operations_with_zero(self):
        self.assertEqual(self.calc.add(0, 0), 0)
        self.assertEqual(self.calc.subtract(0, 0), 0)
        self.assertEqual(self.calc.multiply(0, 0), 0)
        # Division by zero is handled above, but 0/N should be 0
        self.assertEqual(self.calc.divide(0, 5), 0.0)


if __name__ == '__main__':
    unittest.main()
