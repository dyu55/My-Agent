.PHONY: test lint install clean run chat

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	python -m pytest tests/ -v --tb=short

# Run tests with coverage
test-cov:
	python -m pytest tests/ -v --tb=short --cov=agent --cov=utils --cov-report=term-missing

# Check syntax
lint:
	python -m py_compile agent/engine.py
	python -m py_compile agent/planner.py
	python -m py_compile agent/executor.py
	python -m py_compile agent/reflector.py
	python -m py_compile utils/model_provider.py
	python -m py_compile utils/small_model.py
	python -m py_compile utils/llm_cache.py
	python -m py_compile utils/conversation.py
	python -m py_compile main.py

# Run a task
run:
	python main.py "$(TASK)"

# Start interactive CLI
chat:
	python main.py --chat

# Clean temporary files
clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov
	rm -rf workspace/__pycache__
	rm -f .agent_checkpoint.json .agent_trajectory.json
