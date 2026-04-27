"""
WareFlow Unified Backend Launcher

This script starts both the RL Warehouse server (Port 8000)
and the Supply Chain Gateway server (Port 8001) simultaneously.

Usage:
    python run_backend.py
"""

import subprocess
import sys
import time

def main():
    print("=====================================================")
    print("  🚀 Starting WareFlow Unified Backend")
    print("=====================================================")

    # Use sys.executable to ensure we use the same Python environment
    python_exe = sys.executable

    print("\n[1/2] Starting RL Warehouse Server (Port 8000)...")
    p2_process = subprocess.Popen(
        [python_exe, "run_p2_server.py"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    # Small delay to prevent console output from jumbling too much
    time.sleep(2)

    print("\n[2/2] Starting Supply Chain Gateway (Port 8001)...")
    supply_process = subprocess.Popen(
        [python_exe, "run_supply_server.py"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )

    print("\n=====================================================")
    print("  ✅ All backend services are running!")
    print("  -> RL Warehouse   : http://localhost:8000")
    print("  -> Supply Chain   : http://localhost:8001")
    print("  Press Ctrl+C to stop all servers.")
    print("=====================================================\n")

    try:
        # Keep the main process alive while the servers run
        p2_process.wait()
        supply_process.wait()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping all servers...")
        p2_process.terminate()
        supply_process.terminate()
        p2_process.wait()
        supply_process.wait()
        print("[SHUTDOWN] Bye!")

if __name__ == "__main__":
    main()
