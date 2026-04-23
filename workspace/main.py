import sys
import os

# 假设 calculator.py 位于当前目录
# 如果项目结构更复杂，可能需要调整导入路径
from calculator import Calculator

def main():
    """主运行函数：提供用户交互界面来使用计算器功能。"""
    print("========================================")
    print("        Python 命令行计算器 (CLI)        ")
    print("========================================")

    calculator = Calculator()

    while True:
        print("\n请选择操作：")
        print("1. 加法 (+)")
        print("2. 减法 (-)")
        print("3. 乘法 (*)")
        print("4. 除法 (/)")
        print("5. 退出")
        
        choice = input("请输入操作编号 (1-5): ")
        
        if choice == '5':
            print("退出计算器。再见！")
            break
        
        if choice in ('1', '2', '3', '4'):
            try:
                # 接收用户输入，并尝试转换为浮点数
                print("请输入第一个数字：")
                num1 = float(input()) 
                print("请输入第二个数字：")
                num2 = float(input())
            except ValueError:
                print("错误：输入必须是有效的数字。")
                continue
            
            result = None
            operation_symbol = ""

            if choice == '1':
                result = calculator.add(num1, num2)
                operation_symbol = "+"
            elif choice == '2':
                result = calculator.subtract(num1, num2)
                operation_symbol = "-"
            elif choice == '3':
                result = calculator.multiply(num1, num2)
                operation_symbol = "*"
            elif choice == '4':
                # 除法有特殊处理，需要捕获可能的 ZeroDivisionError
                try:
                    result = calculator.divide(num1, num2)
                    operation_symbol = "/"
                except ZeroDivisionError:
                    print("错误：除数不能为零。")
                    continue
            
            if result is not None:
                print(f"\n计算结果：{num1} {operation_symbol} {num2} = {result:.2f}")
        else:
            print("无效的选择，请重新输入。")

if __name__ == "__main__":
    main()
