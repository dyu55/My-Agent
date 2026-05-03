def add(a, b):
    """Adds two numbers."""
    return a + b

def subtract(a, b):
    """Subtracts two numbers."""
    return a - b

def multiply(a, b):
    """Multiplies two numbers."""
    return a * b

def divide(a, b):
    """Divides two numbers. Handles division by zero."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

# Optional: A main function or dispatcher for easy use
OPERATIONS = {
    "+": add,
    "-": subtract,
    "*": multiply,
    "/": divide
}

def calculate(num1, num2, operation):
    """Performs the calculation based on the given operation symbol."""
    if operation in OPERATIONS:
        return OPERATIONS[operation](num1, num2)
    else:
        raise ValueError("Invalid operation symbol. Supported operations: +, -, *, /")
