import asyncio
import time
import json
import logging
import uuid
from typing import Dict, Any
from fastapi import WebSocket

from core.encryption import encrypt_payload, decrypt_payload
from core.rewards import distribute_reward
from core.ledger import create_ledger_block

logger = logging.getLogger(__name__)

class NodeConnection:
    def __init__(self, node_id: str, websocket: WebSocket):
        self.node_id = node_id
        self.websocket = websocket
        self.last_heartbeat = time.time()
        self.status = "Active"
        
    def is_alive(self):
        # 5 second timeout
        return (time.time() - self.last_heartbeat) < 5.0

class SwarmOrchestrator:
    def __init__(self):
        self.active_nodes: Dict[str, NodeConnection] = {}
        
        # Generation State
        self.current_prompt = ""
        self.generated_tokens = 0
        self.max_tokens = 20
        self.is_generating = False
        
        # USP 3: Intermediate State Caching
        self.cached_state = {
            "last_success_stage": 0,
            "hidden_states": None,
            "current_token_index": 0,
            "assigned_node": None
        }
        
        # Frontend WebSocket connection
        self.frontend_ws: WebSocket = None

        # Tracking metrics for the ledger block
        self.session_compute_time = 0.0
        self.session_tokens_processed = 0
        self.node_participations = {}

    async def register_frontend(self, ws: WebSocket):
        self.frontend_ws = ws

    async def broadcast_frontend(self, message: dict):
        if self.frontend_ws:
            try:
                await self.frontend_ws.send_json(message)
            except Exception as e:
                logger.error(f"Frontend broadcast failed: {e}")
                self.frontend_ws = None

    def register_node(self, node_id: str, ws: WebSocket):
        self.active_nodes[node_id] = NodeConnection(node_id, ws)
        logger.info(f"Node Registered: {node_id}")
        self.node_participations[node_id] = 0

    def unregister_node(self, node_id: str):
        if node_id in self.active_nodes:
            self.active_nodes[node_id].status = "Failed"
            logger.warning(f"Node Unregistered/Failed: {node_id}")

    def update_heartbeat(self, node_id: str):
        if node_id in self.active_nodes:
            self.active_nodes[node_id].last_heartbeat = time.time()
            self.active_nodes[node_id].status = "Active"

    async def check_timeouts(self):
        """Watcher loop checking for node timeouts (5s)"""
        while True:
            await asyncio.sleep(1)
            dead_nodes = []
            for node_id, conn in self.active_nodes.items():
                if not conn.is_alive() and conn.status == "Active":
                    logger.warning(f"Timeout detected for {node_id}")
                    conn.status = "Failed"
                    dead_nodes.append(node_id)
                    
                    await self.broadcast_frontend({
                        "event": "node_failed",
                        "node_id": node_id
                    })
                    
            # Fault Tolerance Recovery (USP 3)
            if self.is_generating and self.cached_state["assigned_node"] in dead_nodes:
                logger.warning(f"Active node {self.cached_state['assigned_node']} died mid-generation. Resuming from cache...")
                await self.resume_from_cache()

    def get_available_node(self, exclude_node: str = None) -> str:
        """Simple round-robin or first available load balancer"""
        for node_id, conn in self.active_nodes.items():
            if conn.status == "Active" and node_id != exclude_node:
                return node_id
        return None

    async def start_generation(self, prompt: str):
        self.current_prompt = prompt
        self.generated_tokens = 0
        self.is_generating = True
        self.session_compute_time = 0.0
        self.session_tokens_processed = 0
        
        # Reset Cache
        self.cached_state = {
            "last_success_stage": 0,
            "hidden_states": None,
            "current_token_index": 0,
            "assigned_node": None
        }
        
        logger.info(f"Starting Generation: '{prompt}'")
        await self.execute_stage(1, prompt=self.current_prompt)

    async def resume_from_cache(self):
        """USP 3: Recovery Logic using cached intermediate state"""
        failed_stage = self.cached_state["last_success_stage"] + 1
        
        if failed_stage > 3:
            # Assume it failed while cycling back to stage 1 for the next token
            failed_stage = 1
            
        logger.info(f"Resuming Stage {failed_stage} from cache")
        await self.broadcast_frontend({"event": "reroute_start", "stage": failed_stage})
        
        if failed_stage == 1:
            await self.execute_stage(1, prompt=self.current_prompt)
        else:
            await self.execute_stage(failed_stage, hidden_states=self.cached_state["hidden_states"])

    async def execute_stage(self, stage: int, prompt: str = None, hidden_states: list = None):
        if not self.is_generating:
            return
            
        target_node = self.get_available_node()
        if not target_node:
            logger.error("No active nodes available! Halting generation.")
            self.is_generating = False
            await self.broadcast_frontend({"event": "generation_halted", "reason": "No active nodes"})
            return
            
        task_id = str(uuid.uuid4())[:8]
        self.cached_state["assigned_node"] = target_node
        
        payload = {
            "task_id": task_id,
            "stage": stage,
            "prompt": prompt,
            "hidden_states": hidden_states
        }
        
        # USP 5: Privacy-First Encrypted Processing
        encrypted_payload = encrypt_payload(payload)
        
        # Send to frontend for visualization
        await self.broadcast_frontend({
            "event": "stage_start",
            "stage": stage,
            "node": target_node,
            "nonce_preview": encrypted_payload[:16] + "...",
            "encrypted_preview": encrypted_payload[16:64] + "..."
        })
        
        # Send to Worker
        try:
            ws = self.active_nodes[target_node].websocket
            await ws.send_json({
                "type": "task",
                "payload": encrypted_payload
            })
            logger.info(f"Routed Stage {stage} to {target_node}")
        except Exception as e:
            logger.error(f"Failed to route to {target_node}: {e}")
            self.unregister_node(target_node)
            await self.resume_from_cache()

    async def handle_task_result(self, node_id: str, encrypted_payload: str):
        # USP 5: Decrypt and validate auth tag
        try:
            result = decrypt_payload(encrypted_payload)
        except Exception as e:
            logger.error(f"Failed to decrypt result from {node_id}: {e}")
            return
            
        if result.get("status") != "success":
            logger.error(f"Node {node_id} reported error: {result.get('error_msg')}")
            return
            
        stage = result.get("stage")
        compute_time = result.get("compute_time", 0.0)
        
        # Update metrics
        self.session_compute_time += compute_time
        if stage == 1:
            self.session_tokens_processed += result.get("tokens_processed", 0)
            
        self.node_participations[node_id] += 1
        
        # USP 3: Update Cache
        self.cached_state["last_success_stage"] = stage
        if "hidden_states" in result:
            self.cached_state["hidden_states"] = result["hidden_states"]
            
        # Broadcast metric update
        await self.broadcast_frontend({
            "event": "stage_complete",
            "stage": stage,
            "node": node_id,
            "compute_time": compute_time,
            "token_text": result.get("token_text") if stage == 3 else None
        })
        
        # USP 4: Distribute Reward immediately
        tokens_for_reward = result.get("tokens_processed", 0) if stage == 1 else 0
        reward_earned = distribute_reward(node_id, compute_time, tokens_for_reward)
        logger.info(f"Node {node_id} earned: {reward_earned:.4f} REW")
        
        # Routing next stage
        if stage == 1:
            await self.execute_stage(2, hidden_states=self.cached_state["hidden_states"])
        elif stage == 2:
            await self.execute_stage(3, hidden_states=self.cached_state["hidden_states"])
        elif stage == 3:
            # Token generated
            self.generated_tokens += 1
            self.current_prompt += result["token_text"]
            self.cached_state["current_token_index"] = self.generated_tokens
            
            if self.generated_tokens >= self.max_tokens:
                logger.info("Generation complete (20 tokens reached).")
                self.is_generating = False
                await self.finalize_session()
            else:
                # Loop back to stage 1 for next token
                await self.execute_stage(1, prompt=self.current_prompt)

    async def finalize_session(self):
        """USP 4: Create final ledger block for the session"""
        
        # Give rewards logic in core.rewards.py already saved to DB on a rolling basis.
        # Now create the ledger consensus block.
        
        summary = {
            "total_tokens": self.session_tokens_processed + self.generated_tokens,
            "total_compute": f"{self.session_compute_time:.2f}s",
            "participating_nodes": list({k:v for k,v in self.node_participations.items() if v > 0}.keys())
        }
        
        block_hash = create_ledger_block(summary)
        
        await self.broadcast_frontend({
            "event": "session_complete",
            "ledger_hash": block_hash,
            "summary": summary,
            "final_text": self.current_prompt
        })

# Initialize Global Orchestrator
orchestrator = SwarmOrchestrator()
