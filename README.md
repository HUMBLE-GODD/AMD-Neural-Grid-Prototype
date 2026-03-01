# AMD Neural-Grid Prototype

A complete working prototype of “AMD Neural-Grid” demonstrating a decentralized AI network with multiple nodes, fault tolerance, reputation tracking, crypto rewards, and encrypted computation. 

This system runs completely locally on a single machine using CPU inference and the `distilgpt2` model to ensure it runs comfortably within 16GB RAM.

## The 5 Core USPs Demonstrated

1. **Decentralized AI Inference (True Layer Splitting)**
   The `distilgpt2` model is logically split across 3 simulated edge nodes. 
   - **Node 1**: Embedding + Transformer Layers 0-1
   - **Node 2**: Transformer Layers 2-3
   - **Node 3**: Transformer Layers 4-5 + LM Head & Decoding
   Nodes pass intermediate hidden states back and forth via WebSockets.

2. **Purposeful Compute**
   Instead of hashing random numbers, the network tracks the actual compute time (in seconds) that each node spends processing tensors. This "productive" time is logged in the DB and displayed on the dashboard.

3. **Self-Healing Fault Tolerance**
   The Controller maintains a heartbeat with every node. If a node process is killed mid-generation (simulating a crash), the Controller detects the timeout, seamlessly retrieves the last successful cached hidden state, and re-routes the exact failed stage to another node without losing the generation loop.

4. **Performance-Based Crypto Rewards**
   Nodes earn simulated tokens based on the formula: `(Compute Time * 0.4) + (Tokens * 0.2) + (Uptime * 0.2)`. At the end of every 20-token inference session, a final `LedgerBlock` is created, hashing the summary transaction using SHA256 to simulate an immutable blockchain.

5. **Privacy-First Encrypted Processing**
   Zero-Trust design. Every payload sent between the Controller and the Nodes (including the hidden states) is symmetrically encrypted using `AES-GCM` with a random nonce. The dashboard displays a live preview of this encrypted ciphertext traversing the network.

## Quick Start (Hackathon Ready)

**1. Install Dependencies**
Ensure you are using Python 3.9+ and run:
```bash
pip install -r requirements.txt
```

**2. Launch the Swarm**
Start the Controller and all 3 worker nodes simultaneously:
```bash
python run_demo.py
```
*(The first run will take a moment to download the `distilgpt2` model from HuggingFace to your local cache).*

**3. Open the Dashboard**
Simply open `frontend/index.html` in any modern web browser.

## Using the Dashboard

1. **Start Inference**: Click "Generate (20 Tokens)". Watch the tokens stream in while the topology grid highlights exactly which Node is processing which Stage.
2. **View Encryption**: The right-hand panel shows the AES-GCM Nonce changing per request, proving that the raw hidden states are never sent in plaintext.
3. **Simulate a Crash**: Mid-generation, click the red **Kill Node** button or manually kill one of the Python worker processes in your terminal. Watch the system reroute the task and recover automatically. 
4. **Rewards & Ledger**: View the real-time node balances increasing in the Leaderboard. After the 20th token, the final SHA256 Ledger Block Hash will be securely committed to the SQLite database.

## Architecture Diagram
```ascii
    [User Prompt] 
          |
    (AES-GCM Encrypted)
          v
    [Controller] --- (Heartbeat 2s / 5s Timeout)
          |
          +---> [Node A] (Stage 1: Embed + L0-1)
          |
          +---> [Node B] (Stage 2: L2-3)
          |
          +---> [Node C] (Stage 3: L4-5 + Head)
```

## Built With
* **Backend**: Python, FastAPI, WebSockets
* **AI**: PyTorch, HuggingFace Transformers (`distilgpt2`)
* **Database**: SQLite, SQLAlchemy
* **Security**: Python Cryptography (`AES-GCM`)
* **Frontend**: HTML5, Vanilla JavaScript, TailwindCSS
