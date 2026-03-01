import hashlib
from datetime import datetime
from core.db import SessionLocal, NodeMetrics
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base

# USP 4: Create simple ledger table
Base = declarative_base()

class LedgerBlock(Base):
    __tablename__ = "ledger_blocks"
    
    id = Column(Integer, primary_key=True, index=True)
    previous_hash = Column(String, default="0000000000000000000000000000000000000000000000000000000000000000")
    current_hash = Column(String, unique=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    reward_summary = Column(String)

def init_ledger_db(engine):
    Base.metadata.create_all(bind=engine)

def create_ledger_block(reward_summary_dict: dict):
    db = SessionLocal()
    try:
        last_block = db.query(LedgerBlock).order_by(LedgerBlock.id.desc()).first()
        prev_hash = last_block.current_hash if last_block else "0000000000000000000000000000000000000000000000000000000000000000"
        
        summary_str = str(reward_summary_dict)
        raw_data = f"{prev_hash}{summary_str}{datetime.utcnow().isoformat()}".encode('utf-8')
        curr_hash = hashlib.sha256(raw_data).hexdigest()
        
        new_block = LedgerBlock(
            previous_hash=prev_hash,
            current_hash=curr_hash,
            reward_summary=summary_str
        )
        db.add(new_block)
        db.commit()
        return curr_hash
    finally:
        db.close()
