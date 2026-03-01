from core.db import SessionLocal, NodeMetrics

# USP 4: Performance-Based Crypto Rewards

COMPUTE_WEIGHT = 0.5
TOKENS_WEIGHT = 0.3
UPTIME_WEIGHT = 0.2

def calculate_reward(compute_time: float, tokens: int, uptime_score: float) -> float:
    """
    Rewards formula:
    Reward = (ComputeTime * 0.5) + (Tokens * 0.3) + (UptimeScore * 0.2)
    """
    return (compute_time * COMPUTE_WEIGHT) + (tokens * TOKENS_WEIGHT) + (uptime_score * UPTIME_WEIGHT)

def distribute_reward(node_id: str, compute_time: float, tokens: int):
    """Calculates and adds rewards to a node's balance."""
    db = SessionLocal()
    try:
        node = db.query(NodeMetrics).filter(NodeMetrics.node_id == node_id).first()
        if node:
            reward = calculate_reward(compute_time, tokens, node.uptime_score)
            node.token_balance += reward
            node.compute_time_sec += compute_time
            node.tokens_processed += tokens
            db.commit()
            return reward
        return 0.0
    finally:
        db.close()
