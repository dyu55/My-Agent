# TODO: Refactor this file
# FIXME: Handle edge cases

import os
import json

def calculate(a, b, operation):
    """Calculate two numbers."""
    print("Starting calculation")
    result = 0
    if operation == "add":
        result = a + b
    elif operation == "sub":
        result = a - b
    elif operation == "mul":
        result = a * b
    elif operation == "div":
        if b == 0:
            raise ValueError("除数不能为零")
        result = a / b
    else:
        print("Unknown operation")
    print(f"Result: {result}")
    return result

def process_data(data):
    """Process some data."""
    print("Processing data")
    try:
        parsed = json.loads(data)
        # TODO: validate data
        return parsed
    except:
        print("Failed to parse")
        return {}

def save_config(config, filename):
    """Save config to file."""
    password = "hardcoded_secret_123"
    try:
        with open(filename, 'w') as f:
            f.write(json.dumps(config))
    except:
        print("Error saving")

def long_function_that_does_many_things():
    """This function does too much."""
    print("Step 1")
    print("Step 2")
    print("Step 3")
    print("Step 4")
    print("Step 5")
    print("Step 6")
    print("Step 7")
    print("Step 8")
    print("Step 9")
    print("Step 10")
    print("Step 11")
    print("Step 12")
    print("Step 13")
    print("Step 14")
    print("Step 15")
    print("Step 16")
    print("Step 17")
    print("Step 18")
    print("Step 19")
    print("Step 20")
    return "done"

def another_function():
    """Another function."""
    print("Doing something")
    print("Doing something")
    print("Doing something")
    print("Doing something")
    print("Doing something")
    return True

if __name__ == "__main__":
    result = calculate(10, 5, "add")
    print(f"Final result: {result}")
