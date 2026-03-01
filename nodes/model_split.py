import torch
from transformers import GPT2Tokenizer, GPT2LMHeadModel
import time
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# USP 1: Decentralized AI Supercomputer - True Layer Splitting
# We use distilgpt2 which has 6 transformer layers.
# Structure: Embeddings -> 6x Blocks -> LayerNorm -> LM Head

class SplitModel:
    def __init__(self):
        logger.info("Loading distilgpt2 model (CPU only)...")
        self.tokenizer = GPT2Tokenizer.from_pretrained("distilgpt2")
        self.model = GPT2LMHeadModel.from_pretrained("distilgpt2")
        self.model.eval() # Inference only
        
        # Ensure fixed seed for deterministic reproducible demos
        torch.manual_seed(42)
        
        # Access internals
        self.transformer = self.model.transformer
        self.wte = self.transformer.wte
        self.wpe = self.transformer.wpe
        self.drop = self.transformer.drop
        self.h = self.transformer.h
        self.ln_f = self.transformer.ln_f
        self.lm_head = self.model.lm_head
        
        logger.info("Model loaded successfully.")

    def stage_1(self, prompt: str) -> dict:
        """
        Stage 1: Tokenize + Embeddings + Layers 0-1
        """
        start_time = time.time()
        
        # Tokenize
        inputs = self.tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"]
        
        # Positional ids
        position_ids = torch.arange(0, input_ids.size(-1), dtype=torch.long, device=input_ids.device)
        position_ids = position_ids.unsqueeze(0).view(-1, input_ids.size(-1))
        
        # Embeddings
        inputs_embeds = self.wte(input_ids)
        position_embeds = self.wpe(position_ids)
        hidden_states = inputs_embeds + position_embeds
        hidden_states = self.drop(hidden_states)
        
        # Layer 0 & 1
        for i in range(2):
            outputs = self.h[i](hidden_states)
            hidden_states = outputs[0]
            
        compute_time = time.time() - start_time
        
        # Serialize to CPU-safe list for WebSocket transmission
        hidden_states_list = hidden_states.detach().cpu().numpy().tolist()
        
        return {
            "hidden_states": hidden_states_list,
            "tokens_processed": input_ids.shape[1],
            "compute_time": compute_time
        }

    def stage_2(self, hidden_states_list: list) -> dict:
        """
        Stage 2: Layers 2-3
        """
        start_time = time.time()
        
        # Reconstruct tensor
        hidden_states = torch.tensor(hidden_states_list, dtype=torch.float32)
        
        # Layer 2 & 3
        for i in range(2, 4):
            outputs = self.h[i](hidden_states)
            hidden_states = outputs[0]
            
        compute_time = time.time() - start_time
        
        return {
            "hidden_states": hidden_states.detach().cpu().numpy().tolist(),
            "compute_time": compute_time
        }

    def stage_3(self, hidden_states_list: list) -> dict:
        """
        Stage 3: Layers 4-5 + LM Head + Decode
        """
        start_time = time.time()
        
        # Reconstruct tensor
        hidden_states = torch.tensor(hidden_states_list, dtype=torch.float32)
        
        # Layer 4 & 5
        for i in range(4, 6):
            outputs = self.h[i](hidden_states)
            hidden_states = outputs[0]
            
        # Final Norm
        hidden_states = self.ln_f(hidden_states)
        
        # LM Head predicts next token logits
        lm_logits = self.lm_head(hidden_states)
        
        # Get the next token (greedy approach for deterministic result)
        next_token_logits = lm_logits[0, -1, :]
        next_token_id = torch.argmax(next_token_logits).item()
        
        # Decode
        next_token_text = self.tokenizer.decode([next_token_id])
        
        compute_time = time.time() - start_time
        
        return {
            "token_id": next_token_id,
            "token_text": next_token_text,
            "compute_time": compute_time
        }

# Example usage/tester
if __name__ == "__main__":
    node_model = SplitModel()
    prompt = "The future of AI is"
    print(f"Prompt: {prompt}")
    
    print("\n--- Running Stage 1 ---")
    s1_res = node_model.stage_1(prompt)
    print(f"Stage 1 compute: {s1_res['compute_time']:.4f}s")
    
    print("\n--- Running Stage 2 ---")
    s2_res = node_model.stage_2(s1_res["hidden_states"])
    print(f"Stage 2 compute: {s2_res['compute_time']:.4f}s")
    
    print("\n--- Running Stage 3 ---")
    s3_res = node_model.stage_3(s2_res["hidden_states"])
    print(f"Stage 3 compute: {s3_res['compute_time']:.4f}s")
    print(f"Generated Token: '{s3_res['token_text']}'")
