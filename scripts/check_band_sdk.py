import importlib.util
import sys

for name in ["thenvoi", "band_sdk", "band"]:
    spec = importlib.util.find_spec(name)
    print(f"{name}: {spec}")

try:
    from thenvoi import Agent
    print("thenvoi.Agent OK")
except Exception as e:
    print(f"thenvoi error: {e}")

try:
    import band_sdk
    print(f"band_sdk path: {band_sdk.__file__}")
    print(f"band_sdk dir: {dir(band_sdk)[:20]}")
except Exception as e:
    print(f"band_sdk error: {e}")
