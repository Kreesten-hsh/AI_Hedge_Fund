from openbb import obb

print("Testing DXY via yfinance:")
try:
    res = obb.index.price.historical(symbol="DX-Y.NYB", provider="yfinance", limit=2)
    print(res)
except Exception as e:
    print("Error:", e)

print("\nTesting US10Y via yfinance:")
try:
    res = obb.index.price.historical(symbol="^TNX", provider="yfinance", limit=2)
    print(res)
except Exception as e:
    print("Error:", e)
