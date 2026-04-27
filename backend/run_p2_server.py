import uvicorn
import os
import sys

if __name__ == "__main__":
    print("\n--- Starting WareFlow Disruption Predictor (P2) ---")
    print("   Port: 8000")
    
    # Ensure current directory is in path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload for background stability
    )
