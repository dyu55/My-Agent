import sys
import io
import contextlib

class PythonExecutor:
    """A tool that allows the agent to execute Python code and see the output."""
    
    def execute(self, code: str) -> str:
        """Executes python code and captures stdout."""
        output_buffer = io.StringIO()
        
        # We use a context manager to capture stdout
        try:
            with contextlib.redirect_stdout(output_buffer):
                # We use exec() to run the code. 
                # WARNING: In a real harness, this MUST be in a sandbox (Docker).
                exec(code, {})
            return output_buffer.getvalue()
        except Exception as e:
            return f"Error during execution: {str(e)}"

def run_python_tool(code: str) -> str:
    executor = PythonExecutor()
    return executor.execute(code)
