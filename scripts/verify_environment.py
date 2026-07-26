import sys
import platform
import os
import importlib

def check_package(package_name, min_version=None):
    try:
        if package_name == 'openbb':
            try:
                import openbb_core
                import openbb
                version = getattr(openbb, "__version__", "Found")
            except ImportError:
                return "FAILED", "Not installed"
        elif package_name == 'qlib':
            try:
                import qlib
                version = getattr(qlib, "__version__", "Found")
            except ImportError:
                # pyqlib often installs as qlib
                return "FAILED", "Not installed"
        else:
            mod = importlib.import_module(package_name)
            version = getattr(mod, "__version__", "Found")
        
        # Simple version check logic if needed
        if min_version and version != "Found":
            # Just naive split, could be improved if needed
            v_parts = version.split('.')
            m_parts = min_version.split('.')
            for v, m in zip(v_parts, m_parts):
                try:
                    if int(v.split('-')[0].split('+')[0]) < int(m):
                        return "FAILED", f"{version} < {min_version}"
                    elif int(v.split('-')[0].split('+')[0]) > int(m):
                        break
                except ValueError:
                    pass
        
        return "OK", version
    except ImportError:
        return "FAILED", "Not installed"
    except Exception as e:
        return "FAILED", str(e)

def main():
    print("===================================================")
    print("AEGIS QUANT OS")
    print("Environment Verification")
    print("===================================================\n")
    
    # Python Version
    py_version = sys.version.split()[0]
    py_ok = "3.11" in py_version
    py_status = "OK" if py_ok else "FAIL"
    print(f"Python ............. {py_version} {py_status}")
    
    # Platform
    print(f"Platform ........... {platform.system()} {platform.release()}")
    print(f"Architecture ....... {platform.machine()}")
    
    # sys.executable
    executable = sys.executable
    print(f"Executable ......... {executable}")
    
    # VirtualEnv check
    is_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    is_venv_str = "ACTIVE" if is_venv else "INACTIVE"
    print(f"VirtualEnv ......... {is_venv_str}")
    
    print("\n===================================================\n")
    
    print(f"{'Component':<15} | {'Minimum':<10} | {'Detected':<15} | {'Status'}")
    print("-" * 60)
    
    components = [
        ("Python", "3.11", py_version, "OK" if py_ok else "FAILED"),
    ]
    
    packages = [
        ("OpenBB", "openbb", "4.0"),
        ("Qlib", "qlib", "0.9"),
        ("vn.py", "vnpy", ""),
        ("Pandas", "pandas", ""),
        ("NumPy", "numpy", ""),
        ("PyArrow", "pyarrow", ""),
        ("Pytest", "pytest", ""),
    ]
    
    all_ready = py_ok and is_venv
    
    for display_name, pkg_name, min_ver in packages:
        status, detected = check_package(pkg_name, min_ver)
        if status != "OK":
            all_ready = False
        components.append((display_name, min_ver, detected, status))
    
    for comp, min_v, det, stat in components:
        if comp == "Python":
            continue
        print(f"{comp:<15} | {min_v:<10} | {det:<15} | {stat}")
        
    print("\n===================================================\n")
    
    print("Environment Status")
    print("")
    if all_ready:
        print("READY")
    else:
        print("FAILED")
    
    print("\n===================================================")
    
    if not all_ready:
        sys.exit(1)

if __name__ == "__main__":
    main()
