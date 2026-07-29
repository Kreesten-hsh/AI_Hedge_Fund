import sys
import platform
import importlib
import psutil
import shutil
import os

class Colors:
    PASS = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def report(status, name, message=""):
    if status == "PASS":
        print(f"{name:.<30} {Colors.PASS}[PASS]{Colors.ENDC} {message}")
    elif status == "WARNING":
        print(f"{name:.<30} {Colors.WARN}[WARNING]{Colors.ENDC} {message}")
    else:
        print(f"{name:.<30} {Colors.FAIL}[ERROR]{Colors.ENDC} {message}")

def check_system():
    print(f"\n{Colors.BOLD}--- SYSTEM CHECK ---{Colors.ENDC}")
    os_name = platform.system()
    if os_name == "Linux":
        report("PASS", "Operating System", f"Linux ({platform.release()})")
    else:
        report("WARNING", "Operating System", f"Expected Linux, got {os_name}")
    
    cpu_arch = platform.machine()
    report("PASS", "CPU Architecture", cpu_arch)
    
    # RAM Check
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024**3)
    if total_gb >= 8:
        report("PASS", "Total RAM", f"{total_gb:.2f} GB")
    else:
        report("WARNING", "Total RAM", f"{total_gb:.2f} GB (>= 8GB recommended)")
        
    # Disk Check
    disk = shutil.disk_usage("/")
    free_gb = disk.free / (1024**3)
    if free_gb >= 10:
        report("PASS", "Free Disk Space", f"{free_gb:.2f} GB")
    else:
        report("WARNING", "Free Disk Space", f"{free_gb:.2f} GB (>= 10GB recommended)")

def check_python_env():
    print(f"\n{Colors.BOLD}--- PYTHON ENVIRONMENT ---{Colors.ENDC}")
    # Python Version
    version = sys.version_info
    if version.major == 3 and version.minor == 11:
        report("PASS", "Python Version", sys.version.split()[0])
    else:
        report("ERROR", "Python Version", f"Expected 3.11.x, got {sys.version.split()[0]}")
    
    # Venv Check
    is_venv = (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))
    if is_venv:
        report("PASS", "Virtual Environment", "Active")
    else:
        report("ERROR", "Virtual Environment", "Not running inside a venv")

def check_dependencies():
    print(f"\n{Colors.BOLD}--- CRITICAL DEPENDENCIES ---{Colors.ENDC}")
    deps = [
        "openbb",
        "qlib",
        "vnpy",
        "pandas",
        "numpy",
        "scipy",
        "polars",
        "pyarrow",
        "sklearn", # scikit-learn
        "lightgbm",
        "xgboost",
        "catboost",
        "matplotlib",
        "plotly",
        "pytest",
        "mypy",
        "ruff",
        "black"
    ]
    
    all_pass = True
    for dep in deps:
        try:
            mod = importlib.import_module(dep)
            version = getattr(mod, "__version__", "unknown")
            report("PASS", dep, f"v{version}")
        except ImportError as e:
            report("ERROR", dep, f"ImportFailed: {e}")
            all_pass = False
        except Exception as e:
            report("WARNING", dep, f"Load Warning: {e}")
            
    return all_pass

if __name__ == "__main__":
    check_system()
    check_python_env()
    all_deps = check_dependencies()
    
    print(f"\n{Colors.BOLD}--- CERTIFICATION RESULT ---{Colors.ENDC}")
    if all_deps:
        print(f"{Colors.PASS}Environment is fully certified for Aegis Quant OS.{Colors.ENDC}")
        sys.exit(0)
    else:
        print(f"{Colors.FAIL}Environment certification FAILED. Missing critical dependencies.{Colors.ENDC}")
        sys.exit(1)
