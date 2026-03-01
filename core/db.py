import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./neural_grid.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class NodeMetrics(Base):
    __tablename__ = "node_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, unique=True, index=True)
    status = Column(String, default="Offline")
    compute_time_sec = Column(Float, default=0.0)
    tokens_processed = Column(Integer, default=0)
    uptime_score = Column(Float, default=100.0)
    token_balance = Column(Float, default=0.0)
    success_rate = Column(Float, default=100.0)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    try:
        from core.ledger import init_ledger_db
        init_ledger_db(engine)
    except ImportError:
        pass
        
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
