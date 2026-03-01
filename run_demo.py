import subprocess
import time
import os
import sys

def print_ascii_art():
    print("""
    =======================================================
       AMD Neural-Grid | Decentralized Inference Engine
    =======================================================
    
    [User Prompt] 
          |
    (AES-GCM Encrypted)
          v
    [Controller] --- (Heartbeat 2s)
          |
          +---> [Node A] (Stage 1: Embed + L0-1)
          |
          +---> [Node B] (Stage 2: L2-3)
          |
          +---> [Node C] (Stage 3: L4-5 + Head)
          
    =======================================================
    Starting Swarm...
    """)

processes = []

def start_services():
    try:
        # Start Controller
        print("Starting Controller (FastAPI)...")
        controller_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "controller.server:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.DEVNULL, # Keep logs clean for demo
            stderr=subprocess.PIPE
        )
        processes.append(controller_proc)
        
        # Give controller 3 seconds to init DB and start
        time.sleep(3)
        
        # Start Nodes
        for node_id in ["Node-A", "Node-B", "Node-C"]:
            print(f"Starting {node_id}...")
            proc = subprocess.Popen(
                [sys.executable, "nodes/worker.py", node_id],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            processes.append(proc)
            time.sleep(1) # Stagger starts slightly
            
        print("\n✅ All systems nominal.")
        print("✅ Open 'frontend/index.html' in your browser to view the Neural-Grid Dashboard.")
        print("\nPress Ctrl+C to shut down the swarm gracefully.")
        
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
    print_ascii_art()
    start_services()
