import os
import subprocess
import sys

# 检查src目录
src_path = os.path.join(os.getcwd(), "src")
if not os.path.exists(src_path):
    os.makedirs(src_path)
    print(f"Created src directory: {src_path}")
else:
    print(f"src directory already exists: {src_path}")

# 检查依赖
required_packages = ["fastapi", "uvicorn", "sqlalchemy", "python-jose", "passlib"]
installed = subprocess.run([sys.executable, "-m", "pip", "list", "--format=columns"], capture_output=True, text=True)
installed_packages = installed.stdout.lower()
missing = []
for pkg in required_packages:
    if pkg.lower() in installed_packages:
        print(f"{pkg} is installed.")
    else:
        print(f"{pkg} is NOT installed.")
        missing.append(pkg)
if missing:
    print(f"Missing packages: {', '.join(missing)}")
else:
    print("All required packages are installed.")