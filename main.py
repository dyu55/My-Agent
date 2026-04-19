# 你的线束（指挥官）代码
import os

def main():
    print("Agent Commander initialized.")
    
    # Ensure the workspace directory exists
    if not os.path.exists('workspace'):
        os.makedirs('workspace')
        print("Created 'workspace' directory.")
    else:
        print("'workspace' directory already exists.")

if __name__ == "__main__":
    main()
