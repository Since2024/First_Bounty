
import sys
import os
sys.path.append(os.getcwd())

try:
    print("Importing app.solana_utils...")
    import app.solana_utils
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
