import sys

def main():
    print("==========================================")
    print("VERIFICATION OF MICROSOFT QLIB INSTALLATION")
    print("==========================================")
    try:
        import qlib
        from qlib.config import REG_CN
        
        # Initialize qlib in a dummy provider_uri to not require huge data downloads
        qlib.init(provider_uri="~/.qlib/qlib_data/cn_data", region=REG_CN)
        print(f"[OK] Qlib version {qlib.__version__} is installed and initialized successfully.")
        
    except ImportError as e:
        print(f"[ERROR] Failed to import Qlib: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during Qlib initialization: {e}")
        sys.exit(1)

    print("==========================================")
    print("Verification complete.")
    print("==========================================")

if __name__ == "__main__":
    main()
