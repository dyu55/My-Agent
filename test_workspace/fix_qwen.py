import re
import os
import subprocess

BASE_DIR = 'qwen_output/snippets'

def fix_model_output(content):
    """Fix line-wrapping artifacts in LLM output"""
    lines = content.split('\n')
    fixed = []
    skip_next = False

    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        stripped = line.rstrip()

        # Check if line ends with incomplete statement
        # Patterns: unclosed string, unclosed paren/brackets, trailing comma, etc.
        needs_continuation = False

        # Count quotes - odd means unclosed string
        if stripped.count('"') % 2 == 1:
            needs_continuation = True
        if stripped.count("'") % 2 == 1:
            needs_continuation = True

        # Ends with open paren/brackets/brace
        if stripped.endswith(('(', '[', '{', ',')):
            needs_continuation = True

        # Line is very short and doesn't look complete
        if len(stripped) < 10 and not stripped.endswith((')', ']', '}')):
            needs_continuation = True

        # Check if next line is a continuation
        if needs_continuation and i + 1 < len(lines):
            next_line = lines[i + 1].strip()

            # Continuation lines typically:
            # - Start with a word that completes the previous line
            # - Are indented less or same as current line
            if next_line and not next_line.startswith('#'):
                # Join this line with next line
                joined = stripped + ' ' + next_line
                fixed.append(joined)
                skip_next = True
                continue

        fixed.append(line)

    return '\n'.join(fixed)

# Fix all Python files
for root, dirs, files in os.walk(BASE_DIR):
    for filename in files:
        if filename.endswith('.py'):
            filepath = os.path.join(root, filename)
            with open(filepath, 'r') as f:
                content = f.read()

            # Remove ANSI codes
            content = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]', '', content)

            # Fix wrapped lines
            fixed = fix_model_output(content)

            with open(filepath, 'w') as f:
                f.write(fixed)
            print(f"Fixed: {filename}")

# Try to run it
os.chdir(BASE_DIR)
result = subprocess.run(['python3', '-m', 'src.main', 'list'],
                       capture_output=True, text=True)
print(f"\nTest run 'list' command:")
print(f"Exit code: {result.returncode}")
if result.stdout:
    print(f"Stdout:\n{result.stdout}")
if result.stderr:
    print(f"Stderr:\n{result.stderr[:1000]}")
