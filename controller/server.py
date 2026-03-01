import asyncio
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.db import init_db, SessionLocal, NodeMetrics
from core.ledger import LedgerBlock
from controller.orchestrator import orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AMD Neural-Grid Controller")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()
    # Start the timeout watcher
    asyncio.create_task(orchestrator.check_timeouts())
    logger.info("Database initialized and watcher started.")

# --- WebSockets ---

@app.websocket("/ws/frontend")
async def frontend_ws(websocket: WebSocket):
    await websocket.accept()
    await orchestrator.register_frontend(websocket)
    try:
        while True:
            # We don't expect much from frontend except maybe keepalives
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        orchestrator.frontend_ws = None
        logger.info("Frontend disconnected")

@app.websocket("/ws/node/{node_id}")
async def node_ws(websocket: WebSocket, node_id: str):
    await websocket.accept()
    orchestrator.register_node(node_id, websocket)
    
    # Send initial connections update to frontend
    await orchestrator.broadcast_frontend({
        "event": "system_status",
        "nodes": list(orchestrator.active_nodes.keys())
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("type") == "heartbeat":
                orchestrator.update_heartbeat(node_id)
            elif msg.get("type") == "task_result":
                # Handle async result execution
                asyncio.create_task(orchestrator.handle_task_result(node_id, msg.get("payload")))
                
    except WebSocketDisconnect:
        orchestrator.unregister_node(node_id)
        await orchestrator.broadcast_frontend({
            "event": "node_failed",
            "node_id": node_id
        })

# --- REST APIs for Frontend ---

class PromptRequest(BaseModel):
    prompt: str

@app.post("/api/generate")
async def start_generation(req: PromptRequest):
    if orchestrator.is_generating:
        return {"status": "error", "message": "Already generating"}
        
    # Start generation in background
    asyncio.create_task(orchestrator.start_generation(req.prompt))
    return {"status": "started", "prompt": req.prompt}

@app.get("/api/metrics")
def get_metrics():
    db = SessionLocal()
    try:
        nodes = db.query(NodeMetrics).all()
        last_block = db.query(LedgerBlock).order_by(LedgerBlock.id.desc()).first()
        node_results = []
        active_ids = set(orchestrator.active_nodes.keys())
        
        for n in nodes:
            node_results.append({
                "node_id": n.node_id,
                "status": orchestrator.active_nodes[n.node_id].status if n.node_id in orchestrator.active_nodes else "Offline",
                "compute_time": n.compute_time_sec,
                "tokens": n.tokens_processed,
                "balance": n.token_balance
            })
            if n.node_id in active_ids:
                active_ids.remove(n.node_id)
                
        for node_id in active_ids:
            node_results.append({
                "node_id": node_id,
                "status": orchestrator.active_nodes[node_id].status,
                "compute_time": 0.0,
                "tokens": 0,
                "balance": 0.0
            })
            
        return {
            "nodes": node_results,
            "ledger_hash": last_block.current_hash if last_block else "None"
        }
    finally:
        db.close()
