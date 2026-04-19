import re

class SimpleAgent:
    def __init__(self, llm_provider):
        """
        llm_provider: An object that has a .generate(prompt) method.
        """
        self.llm = llm_provider
        self.tools = {
            "execute_python": run_python_tool
        }
        self.history = []

    def run(self, user_prompt: str):
        print(f"--- Starting Agent Task: {user_prompt} ---")
        self.history.append({"role": "user", "content": user_prompt})
        
        # The ReAct Loop (Limit to 5 iterations to prevent infinite loops)
        for i in range(5):
            # 1. Ask the LLM to reason and act
            prompt = self._build_prompt()
            response = self.llm.generate(prompt)
            self.history.append({"role": "assistant", "content": response})
            
            print(f"\n[Iteration {i+1}]")
            print(f"Agent Thought/Action:\n{response}")

            # 2. Parse the response for a "Tool Call"
            # We look for a specific pattern: ACTION: tool_name | CODE: code_content
            action_match = re.search(r"ACTION:\s*(\w+)\s*\| CODE:\s*(.*)", response, re.DOTALL)
            
            if not action_match:
                print("Agent finished or provided no actionable command.")
                break
                
            tool_name = action_match.group(1)
            tool_code = action_match.group(2).strip()

            if tool_name in self.tools:
                print(f"Executing Tool: {tool_name}...")
                # 3. Execute the tool
                observation = self.tools[tool_name](tool_code)
                print(f"Observation:\n{observation}")
                
                # 4. Feed the observation back into the history
                self.history.append({"role": "system", "content": f"Observation: {observation}"})
            else:
                print(f"Unknown tool: {tool_name}")
                break

    def _build_prompt(self) -> str:
        prompt = "You are a coding assistant. You can use tools to solve problems.\n"
        prompt += "Available Tools:\n- execute_python: Executes python code. Format: ACTION: execute_python | CODE: <code_here>\n"
        prompt += "Format your response as: ACTION: tool_name | CODE: code_content\n"
        prompt += "When you have the final answer, simply state it.\n\n"
        
        for entry in self.history:
            prompt += f"{entry['role'].upper()}: {entry['content']}\n"
        return prompt

# Import the tool function into the engine scope for the regex to work
from agent.tools import run_python_tool
