import unittest
from calculator import Calculator

class TestCalculator(unittest.TestCase):
    def setUp(self):
        # 设置测试用的 Calculator 实例
        self.calc = Calculator()

    def test_addition(self):
        # 测试加法
        self.assertEqual(self.calc.add(5, 3), 8)
        self.assertEqual(self.calc.add(-1, 1), 0)
        self.assertEqual(self.calc.add(-5, -5), -10)

    def test_subtraction(self):
        # 测试减法
        self.assertEqual(self.calc.subtract(10, 4), 6)
        self.assertEqual(self.calc.subtract(4, 10), -6)
        self.assertEqual(self.calc.subtract(-5, 5), -10)

    def test_multiplication(self):
        # 测试乘法
        self.assertEqual(self.calc.multiply(2, 3), 6)
        self.assertEqual(self.calc.multiply(-2, 3), -6)
        self.assertEqual(self.calc.multiply(-2, -3), 6)

    def test_division_success(self):
        # 测试正常除法
        self.assertEqual(self.calc.divide(10, 2), 5.0)
        self.assertEqual(self.calc.divide(10, 3), 3.3333333333333335)
        self.assertEqual(self.calc.divide(-10, 2), -5.0)

    def test_division_by_zero(self):
        # 测试除零异常
        with self.assertRaises(ZeroDivisionError):
            self.calc.divide(10, 0)

    def test_type_handling(self):
        # 测试输入类型错误（可选，取决于 Calculator 的实现）
        # 假设 Calculator 内部会处理非数字输入
        with self.assertRaises(TypeError):
            self.calc.add(5, 'a')

if __name__ == '__main__':
    unittest.main()
