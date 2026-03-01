# AMD Neural-Grid Prototype

A complete working prototype of "AMD Neural-Grid" demonstrating a decentralized AI network with multiple nodes, fault tolerance, reputation tracking, crypto rewards, and encrypted computation. 

This system runs locally using CPU inference and the `distilgpt2` model (16GB RAM safe). It supports both **single-laptop demo mode** (multiple processes) and **real two-laptop distributed mode** (Wi-Fi WebSocket).

## The 5 Core USPs Demonstrated

1. **Decentralized AI Inference (True Layer Splitting)**
   The `distilgpt2` model is logically split across 3 edge nodes. 
   - **Node A**: Embedding + Transformer Layers 0-1
   - **Node B**: Transformer Layers 2-3
   - **Node C**: Transformer Layers 4-5 + LM Head & Decoding
   Nodes pass intermediate hidden states via encrypted WebSockets.

2. **Purposeful Compute**
   The network tracks actual compute time (in seconds) per node. This "productive" time is logged in the DB and shown on the dashboard — no wasted hash cycles.

3. **Self-Healing Fault Tolerance**
   Click the **Kill Node** button mid-generation to simulate a crash. The Controller instantly detects the disconnect, retrieves the cached hidden state, and re-routes the failed stage to another live node. Generation continues from the exact token it left off — no restart.

4. **Performance-Based Crypto Rewards**
   Nodes earn tokens: `(Compute * 0.5) + (Tokens * 0.3) + (Uptime * 0.2)`. After every 20-token session, a `LedgerBlock` is committed with SHA256 hash chaining to simulate an immutable blockchain.

5. **Privacy-First Encrypted Processing**
   Every payload between Controller and Nodes is encrypted with `AES-GCM` + random nonce. The dashboard displays live encrypted ciphertext and auth tag verification.

## Quick Start

### Option A: Single-Laptop Demo (Video Recording)
```bash
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt   # Windows
python run_demo.py
```
This boots the Controller + 3 worker nodes automatically. Open `frontend/index.html` in your browser.

### Option B: Two-Laptop Distributed Mode
**Laptop 1 (Controller):**
```bash
python run_demo.py
```
It prints your local IPv4 and the WebSocket URL.

**Laptop 2 (Workers):**
Edit `CONTROLLER_WS_URL` in `nodes/worker.py` to `ws://<LAPTOP1_IP>:8000/ws`, then:
```bash
python nodes/worker.py Node-A
python nodes/worker.py Node-B
python nodes/worker.py Node-C
```

## Using the Dashboard

1. **Start Inference**: Click "Generate (20 Tokens)". Watch tokens stream while the stage grid highlights which Node processes which Stage.
2. **View Encryption**: The panel shows the AES-GCM Nonce changing per request, proving hidden states are never sent in plaintext.
3. **Simulate a Crash**: Click the red **Kill Node** button mid-generation. Watch the node turn red, the overlay announce reassignment, and generation continue on a new node.
4. **Rewards & Ledger**: View real-time node balances increasing. After the 20th token, the SHA256 Ledger Block Hash is committed.

## Console Output (Demo Video Reference)
```
AMD Neural-Grid Demo Mode Active
All 5 USPs Ready for Demonstration

Controller Started
Node-A Started
Node-B Started
Node-C Started
✅ [Swarm] Node Connected: Node-A
✅ [Swarm] Node Connected: Node-B
✅ [Swarm] Node Connected: Node-C

[Node-A] Executing Stage 1
🔐 Payload Encrypted | Nonce: ... | Preview: ...
🔐 Auth Tag Verified successfully.
[Node-A] Compute Time: 0.045 seconds

Kill Command Received for Node-A
❌ Node-A Disconnected
Stage Reassigned Due to Node Failure
Resuming from Cached Hidden State
Reassigning Stage 2 from Node-A to Node-B

Ledger Block Created
Previous Hash: 0000000000000000...
Current Hash: e51278991587feb2...
```

## Architecture
```
    [User Prompt] 
          |
    (AES-GCM Encrypted)
          v
    [Controller] --- (Heartbeat 2s / 5s Timeout)
          |
          +--> [Node A] (Stage 1: Embed + L0-1)
          |
          +--> [Node B] (Stage 2: L2-3)
          |
          +--> [Node C] (Stage 3: L4-5 + Head)
```

## Built With
* **Backend**: Python, FastAPI, WebSockets
* **AI**: PyTorch, HuggingFace Transformers (`distilgpt2`)
* **Database**: SQLite, SQLAlchemy
* **Security**: Python Cryptography (`AES-GCM`)
* **Frontend**: HTML5, Vanilla JavaScript, TailwindCSS
