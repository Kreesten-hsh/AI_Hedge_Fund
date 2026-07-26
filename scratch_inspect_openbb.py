from openbb import obb

print("Available endpoints in obb.equity.price.historical:")
try:
    print(dir(obb.equity.price.historical))
    print("Help for obb.equity.price.historical:")
    help(obb.equity.price.historical)
except Exception as e:
    print(f"Error accessing obb.equity.price.historical: {e}")

print("\nAvailable endpoints in obb.index.price.historical:")
try:
    print(dir(obb.index.price.historical))
    print("Help for obb.index.price.historical:")
    help(obb.index.price.historical)
except Exception as e:
    print(f"Error accessing obb.index.price.historical: {e}")

print("\nAvailable endpoints in obb.economy:")
try:
    print(dir(obb.economy))
except Exception as e:
    print(f"Error accessing obb.economy: {e}")
