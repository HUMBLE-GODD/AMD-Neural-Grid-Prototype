import asyncio
import websockets
import json
import logging
import sys
import os

# Ensure the root directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model_split import SplitModel
from core.encryption import encrypt_payload, decrypt_payload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CONTROLLER_WS_URL = "ws://127.0.0.1:8000/ws"

class NeuralNode:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.model = SplitModel()
        self.websocket = None
        self.running = False

    async def connect(self):
        self.running = True
        try:
            async with websockets.connect(CONTROLLER_WS_URL) as websocket:
                self.websocket = websocket
                logger.info(f"Node {self.node_id} connected to Swarm Controller.")
                
                # Start heartbeat and listener concurrently
                await asyncio.gather(
                    self.heartbeat_loop(),
                    self.listen_loop()
                )
        except Exception as e:
            logger.error(f"Node {self.node_id} failed to connect: {e}. Retrying in 3s...")
            await asyncio.sleep(3)
            # Reconnect automatically
            if self.running:
                await self.connect()

    async def heartbeat_loop(self):
        """USP 3: Send heartbeat every 2 seconds."""
        while self.running and self.websocket:
            try:
                ping_msg = {"type": "heartbeat", "node_id": self.node_id}
                await self.websocket.send(json.dumps(ping_msg))
                await asyncio.sleep(2)
            except websockets.ConnectionClosed:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break

    async def listen_loop(self):
        """Listen for assigned inference stages."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                
                if data.get("type") == "kill":
                    print("Worker Process Terminated")
                    import os
                    os._exit(1)
                
                if data.get("type") == "task":
                    # USP 5: Privacy-First Encrypted Processing
                    # Decrypt the payload
                    encrypted_payload = data.get("payload")
                    try:
                        task_data = decrypt_payload(encrypted_payload)
                    except Exception as e:
                        logger.error(f"Failed to decrypt task: {e}")
                        continue
                        
                    stage = task_data.get("stage")
                    prompt = task_data.get("prompt")
                    hidden_states_list = task_data.get("hidden_states")
                    task_id = task_data.get("task_id")
                    
                    print(f"[{self.node_id}] Executing Stage {stage}")
                    
                    # Execute assigned stage (USP 1)
                    result = {}
                    try:
                        if stage == 1:
                            result = self.model.stage_1(prompt)
                        elif stage == 2:
                            result = self.model.stage_2(hidden_states_list)
                        elif stage == 3:
                            result = self.model.stage_3(hidden_states_list)
                        else:
                            raise ValueError(f"Unknown stage {stage}")
                            
                        # Add tracking metadata (USP 2 proxy metrics)
                        result["type"] = "task_result"
                        result["task_id"] = task_id
                        result["stage"] = stage
                        result["node_id"] = self.node_id
                        result["status"] = "success"
                        
                        if "compute_time" in result:
                            print(f"[{self.node_id}] Compute Time: {result['compute_time']:.3f} seconds")
                        
                    except Exception as e:
                        logger.error(f"Error executing stage {stage}: {e}")
                        result = {
                            "type": "task_result",
                            "task_id": task_id,
                            "stage": stage,
                            "node_id": self.node_id,
                            "status": "error",
                            "error_msg": str(e)
                        }

                    # Re-encrypt result before sending back
                    encrypted_result = encrypt_payload(result)
                    response_msg = {
                        "type": "task_result",
                        "node_id": self.node_id,
                        "payload": encrypted_result
                    }
                    
                    await self.websocket.send(json.dumps(response_msg))
                    # logger.info(f"Completed Task {task_id} -> Result Sent (Encrypted)")

        except websockets.ConnectionClosed:
            logger.info("Connection closed by server.")
        except Exception as e:
            logger.error(f"Listen loop error: {e}")

    def stop(self):
        self.running = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())

if __name__ == "__main__":
    import sys
    # Node ID passed as argument, e.g., 'python nodes/worker.py Node-A'
    node_id = sys.argv[1] if len(sys.argv) > 1 else "Node-A"
    
    node = NeuralNode(node_id)
    try:
        asyncio.run(node.connect())
    except KeyboardInterrupt:
        logger.info(f"Shutting down {node_id}...")
        node.stop()
