"""
FastAPI webhook server for receiving signals and exposing APIs
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
import asyncio
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.config.logging_config import logger
from src.models.database import init_database, get_db, OperationalSignal, TaskExecution
from src.agents.orchestrator_agent import orchestrator_agent
from src.agents.gmail_monitor import gmail_monitor
from src.agents.sheets_monitor import sheets_monitor

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered operations command center with multi-tool orchestration"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API
class SignalCreate(BaseModel):
    """Model for creating new signal"""
    source: str = Field(..., description="Signal source (gmail, slack, sheets, manual)")
    signal_type: str = Field(..., description="Type of signal")
    subject: str = Field(..., description="Signal subject/title")
    content: str = Field(..., description="Signal content/description")
    sender: str = Field(default="", description="Signal sender")
    metadata: Optional[Dict] = Field(default={}, description="Additional metadata")


class SignalResponse(BaseModel):
    """Model for signal response"""
    signal_id: str
    status: str
    priority_score: Optional[float]
    message: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str


# Background monitoring task
monitoring_task = None


@app.on_event("startup")
async def startup_event():
    """Initialize database and start background monitoring"""
    logger.info("Starting AI Operations Command Center...")
    
    # Initialize database
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
    
    # Start background monitoring
    global monitoring_task
    monitoring_task = asyncio.create_task(run_monitoring_loop())
    logger.info("Background monitoring started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down AI Operations Command Center...")
    
    # Cancel monitoring task
    if monitoring_task:
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
    
    logger.info("Shutdown complete")


async def run_monitoring_loop():
    """Background task that continuously monitors sources"""
    logger.info("Monitoring loop started")
    
    while True:
        try:
            # Monitor Gmail
            gmail_signals = await gmail_monitor.monitor_inbox()
            
            # Monitor Google Sheets
            sheets_signals = await sheets_monitor.monitor_sheets()
            
            # Combine all signals
            all_signals = gmail_signals + sheets_signals
            
            # Process each signal
            if all_signals:
                logger.info(f"Processing {len(all_signals)} signals from monitoring")
                
                db = next(get_db())
                try:
                    for signal_data in all_signals:
                        await orchestrator_agent.process_signal(signal_data, db)
                finally:
                    db.close()
            
            # Wait before next check (60 seconds)
            await asyncio.sleep(60)
            
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in monitoring loop: {str(e)}")
            await asyncio.sleep(60)


# API Endpoints

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check"""
    return HealthResponse(
        status="operational",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version
    )


@app.post("/api/signals", response_model=SignalResponse)
async def create_signal(
    signal: SignalCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create new operational signal and process it
    
    This endpoint allows external systems to submit signals manually
    or via webhooks (e.g., Slack events, custom integrations)
    """
    try:
        logger.info(f"Received new signal via API: {signal.source}/{signal.signal_type}")
        
        # Convert to dict for processing
        signal_data = {
            'source': signal.source,
            'type': signal.signal_type,
            'subject': signal.subject,
            'content': signal.content,
            'sender': signal.sender,
            'metadata': signal.metadata or {}
        }
        
        # Process signal in background
        result = await orchestrator_agent.process_signal(signal_data, db)
        
        return SignalResponse(
            signal_id=result['signal_id'],
            status=result['status'],
            priority_score=result.get('priority_score'),
            message=f"Signal processed successfully with priority {result.get('priority_score', 'N/A')}"
        )
        
    except Exception as e:
        logger.error(f"Error creating signal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/signals", response_model=List[Dict])
async def list_signals(
    limit: int = 50,
    status: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List recent operational signals with optional filtering
    """
    try:
        query = db.query(OperationalSignal)
        
        if status:
            query = query.filter(OperationalSignal.status == status)
        
        if source:
            query = query.filter(OperationalSignal.source == source)
        
        signals = query.order_by(OperationalSignal.detected_at.desc()).limit(limit).all()
        
        return [
            {
                'signal_id': s.signal_id,
                'source': s.source,
                'type': s.signal_type,
                'priority_score': s.priority_score,
                'status': s.status,
                'subject': s.subject,
                'summary': s.ai_summary,
                'assigned_to': s.assigned_to,
                'detected_at': s.detected_at.isoformat(),
                'trello_card_id': s.trello_card_id,
                'notion_page_id': s.notion_page_id
            }
            for s in signals
        ]
        
    except Exception as e:
        logger.error(f"Error listing signals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/signals/{signal_id}", response_model=Dict)
async def get_signal(signal_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific signal
    """
    try:
        signal = db.query(OperationalSignal).filter(
            OperationalSignal.signal_id == signal_id
        ).first()
        
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        
        # Get task executions for this signal
        executions = db.query(TaskExecution).filter(
            TaskExecution.signal_id == signal_id
        ).all()
        
        return {
            'signal_id': signal.signal_id,
            'source': signal.source,
            'type': signal.signal_type,
            'priority_score': signal.priority_score,
            'status': signal.status,
            'subject': signal.subject,
            'description': signal.description,
            'sender': signal.sender,
            'ai_summary': signal.ai_summary,
            'ai_reasoning': signal.ai_reasoning,
            'recommended_action': signal.recommended_action,
            'assigned_to': signal.assigned_to,
            'trello_card_id': signal.trello_card_id,
            'notion_page_id': signal.notion_page_id,
            'slack_message_id': signal.slack_message_id,
            'detected_at': signal.detected_at.isoformat(),
            'processed_at': signal.processed_at.isoformat() if signal.processed_at else None,
            'completed_at': signal.completed_at.isoformat() if signal.completed_at else None,
            'task_executions': [
                {
                    'tool': e.tool_name,
                    'action': e.action,
                    'status': e.status,
                    'started_at': e.started_at.isoformat(),
                    'completed_at': e.completed_at.isoformat() if e.completed_at else None
                }
                for e in executions
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting signal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats", response_model=Dict)
async def get_statistics(db: Session = Depends(get_db)):
    """
    Get operational statistics and metrics
    """
    try:
        total_signals = db.query(OperationalSignal).count()
        pending_signals = db.query(OperationalSignal).filter(
            OperationalSignal.status == 'pending'
        ).count()
        completed_signals = db.query(OperationalSignal).filter(
            OperationalSignal.status == 'completed'
        ).count()
        failed_signals = db.query(OperationalSignal).filter(
            OperationalSignal.status == 'failed'
        ).count()
        
        # Get average priority score
        from sqlalchemy import func
        avg_priority = db.query(func.avg(OperationalSignal.priority_score)).scalar() or 0
        
        # Get signals by source
        from sqlalchemy import func
        signals_by_source = db.query(
            OperationalSignal.source,
            func.count(OperationalSignal.id)
        ).group_by(OperationalSignal.source).all()
        
        return {
            'total_signals': total_signals,
            'pending': pending_signals,
            'completed': completed_signals,
            'failed': failed_signals,
            'average_priority': round(avg_priority, 2),
            'signals_by_source': {source: count for source, count in signals_by_source},
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-signal")
async def create_test_signal(db: Session = Depends(get_db)):
    """
    Create a test signal for demonstration purposes
    """
    test_signal = SignalCreate(
        source="manual",
        signal_type="customer_complaint",
        subject="Test: Customer unhappy with delivery delay",
        content="""
        Dear Support,
        
        I am extremely disappointed with the service. My order #12345 was supposed 
        to arrive 3 days ago but I still haven't received it. This is unacceptable.
        I need this resolved immediately or I want a full refund.
        
        This is my third complaint about this issue and nobody has responded properly.
        
        Regards,
        Frustrated Customer
        """,
        sender="customer@example.com",
        metadata={
            'order_id': '12345',
            'delay_days': 3,
            'complaint_count': 3
        }
    )
    
    signal_data = {
        'source': test_signal.source,
        'type': test_signal.signal_type,
        'subject': test_signal.subject,
        'content': test_signal.content,
        'sender': test_signal.sender,
        'metadata': test_signal.metadata
    }
    
    result = await orchestrator_agent.process_signal(signal_data, db)
    
    return {
        'message': 'Test signal created and processed',
        'result': result
    }


# Webhook endpoint for Slack
@app.post("/webhooks/slack")
async def slack_webhook(payload: Dict, db: Session = Depends(get_db)):
    """
    Handle incoming Slack webhooks
    This can process Slack events like mentions, messages in specific channels, etc.
    """
    try:
        logger.info("Received Slack webhook")
        
        # Process Slack event
        event = payload.get('event', {})
        event_type = event.get('type')
        
        if event_type == 'message':
            # Extract message details
            text = event.get('text', '')
            user = event.get('user', '')
            channel = event.get('channel', '')
            
            # Create signal from Slack message
            signal_data = {
                'source': 'slack',
                'type': 'slack_message',
                'subject': f'Slack message from {user}',
                'content': text,
                'sender': user,
                'metadata': {
                    'channel': channel,
                    'event_type': event_type
                }
            }
            
            await orchestrator_agent.process_signal(signal_data, db)
        
        return {'status': 'ok'}
        
    except Exception as e:
        logger.error(f"Error processing Slack webhook: {str(e)}")
        return {'status': 'error', 'message': str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.webhooks.api_server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
