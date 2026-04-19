from agent.engine import SimpleAgent

class MockLLM:
    """
    A Mock LLM to demonstrate the loop without needing an API key.
    In a real scenario, this would call OpenAI or Anthropic.
    """
    def generate(self, prompt: str) -> str:
        # We simulate a 'Reasoning' step and an 'Action' step
        if "calculate the square root of 16" in prompt.lower():
            return "ACTION: execute_python | CODE: import math; print(math.sqrt(16))"
        
        if "Observation: 4.0" in prompt:
            return "The square root of 16 is 4.0. Task complete."
            
        return "I am not sure how to help with that."

if __name__ == "__main__":
    # Initialize our Mock LLM
    mock_llm = MockLLM()
    
    # Initialize the Agent
    agent = SimpleAgent(llm_provider=mock_llm)
    
    # Run a task
    agent.run("Please calculate the square root of 16 using python.")
