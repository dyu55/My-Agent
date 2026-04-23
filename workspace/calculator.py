class Calculator:
    """
    一个简单的计算器类，提供加、减、乘、除功能。
    """
    def add(self, a: float, b: float) -> float:
        """计算两个数之和。
        """ 
        return a + b

    def subtract(self, a: float, b: float) -> float:
        """计算两个数的差。
        """ 
        return a - b

    def multiply(self, a: float, b: float) -> float:
        """计算两个数的积。
        """ 
        return a * b

    def divide(self, a: float, b: float) -> float:
        """计算两个数之比。如果除数b为0，则抛出ZeroDivisionError。
        """ 
        if b == 0:
            raise ZeroDivisionError("不能除以零")
        return a / b
