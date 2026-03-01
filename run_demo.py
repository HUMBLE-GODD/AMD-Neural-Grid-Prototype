import subprocess
import sys
import time
import os

def print_banner():
    print("\n=======================================================")
    print("   AMD Neural-Grid | Decentralized Inference Engine")
    print("=======================================================\n")
    print("AMD Neural-Grid Demo Mode Active")
    print("All 5 USPs Ready for Demonstration\n")

processes = []

def start_swarm():
    try:
        # 1. Start Controller
        controller_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "controller.server:app", "--host", "0.0.0.0", "--port", "8000"]
        )
        processes.append(controller_proc)
        print("Controller Started")
        
        # 2. Wait 2 seconds for controller to bind
        time.sleep(2)
        
        # 3. Start 3 Worker Nodes
        for node_id in ["Node-A", "Node-B", "Node-C"]:
            proc = subprocess.Popen(
                [sys.executable, "nodes/worker.py", node_id]
            )
            processes.append(proc)
            print(f"{node_id} Started")
            time.sleep(0.5) # Stagger starts slightly so logs are clean
            
        print("\n✅ Swarm is online. Open 'frontend/index.html' in your browser.")
        print("Press Ctrl+C to shut down gracefully.\n")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down Swarm...")
        shutdown()

def shutdown():
    for p in processes:
        p.terminate()
    print("Goodbye.")

if __name__ == "__main__":
    print_banner()
    start_swarm()
