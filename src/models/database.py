"""
Database models and setup for Operations Command Center
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from src.config.settings import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.debug
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


class OperationalSignal(Base):
    """Model for storing operational signals detected from various sources"""
    __tablename__ = 'operational_signals'
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String(100), unique=True, index=True, nullable=False)
    source = Column(String(50), nullable=False, index=True)  # gmail, slack, sheets
    signal_type = Column(String(50), nullable=False)  # urgent_email, deadline, complaint
    priority_score = Column(Float, nullable=False, index=True)
    status = Column(String(20), default='pending', index=True)  # pending, processing, completed, failed
    
    # Signal content
    subject = Column(String(500))
    description = Column(Text)
    sender = Column(String(200))
    raw_data = Column(Text)
    
    # AI Analysis
    ai_summary = Column(Text)
    ai_reasoning = Column(Text)
    recommended_action = Column(Text)
    
    # Orchestration tracking
    trello_card_id = Column(String(100))
    notion_page_id = Column(String(100))
    slack_message_id = Column(String(100))
    assigned_to = Column(String(200))
    
    # Timestamps
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Metadata
    retries = Column(Integer, default=0)
    error_message = Column(Text)
    
    def __repr__(self):
        return f"<OperationalSignal(id={self.id}, type={self.signal_type}, priority={self.priority_score})>"


class TaskExecution(Base):
    """Model for tracking task execution across tools"""
    __tablename__ = 'task_executions'
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String(100), index=True, nullable=False)
    tool_name = Column(String(50), nullable=False)  # gmail, trello, notion, slack, drive
    action = Column(String(100), nullable=False)  # create_card, send_message, create_page
    
    # Execution details
    status = Column(String(20), default='pending')  # pending, success, failed
    request_data = Column(Text)
    response_data = Column(Text)
    error_message = Column(Text)
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    
    def __repr__(self):
        return f"<TaskExecution(id={self.id}, tool={self.tool_name}, status={self.status})>"


class MetricsLog(Base):
    """Model for storing system metrics and performance data"""
    __tablename__ = 'metrics_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    metric_type = Column(String(50), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20))
    
    # Context
    source = Column(String(50))
    description = Column(Text)
    
    # Timestamp
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<MetricsLog(type={self.metric_type}, value={self.metric_value})>"


def init_database():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
