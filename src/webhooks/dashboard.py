"""
Real-time metrics dashboard for operations monitoring
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from datetime import datetime, timedelta
from src.models.database import SessionLocal, OperationalSignal, TaskExecution

router = APIRouter()

@router.get("/dashboard", response_class=HTMLResponse)
async def live_dashboard(request: Request):
    """Live metrics dashboard"""
    db = SessionLocal()
    
    try:
        # Get statistics
        total_signals = db.query(OperationalSignal).count()
        today_signals = db.query(OperationalSignal).filter(
            OperationalSignal.detected_at >= datetime.utcnow() - timedelta(days=1)
        ).count()
        
        avg_priority = db.query(func.avg(OperationalSignal.priority_score)).scalar() or 0
        
        high_priority = db.query(OperationalSignal).filter(
            OperationalSignal.priority_score >= 8
        ).count()
        
        # Get recent signals
        recent = db.query(OperationalSignal).order_by(
            OperationalSignal.detected_at.desc()
        ).limit(10).all()
        
        # Get execution stats
        total_executions = db.query(TaskExecution).count()
        successful = db.query(TaskExecution).filter(
            TaskExecution.status == 'success'
        ).count()
        
        success_rate = (successful / total_executions * 100) if total_executions > 0 else 0
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Operations Command Center - Live Dashboard</title>
            <meta http-equiv="refresh" content="5">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px;
                }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                h1 {{ 
                    color: white; 
                    text-align: center; 
                    margin-bottom: 30px;
                    font-size: 2.5em;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                }}
                .metrics {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .metric-card {{
                    background: white;
                    border-radius: 15px;
                    padding: 25px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    transition: transform 0.3s;
                }}
                .metric-card:hover {{ transform: translateY(-5px); }}
                .metric-value {{ 
                    font-size: 3em; 
                    font-weight: bold; 
                    color: #667eea;
                    margin: 10px 0;
                }}
                .metric-label {{ 
                    color: #666; 
                    font-size: 0.9em;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                .signals-table {{
                    background: white;
                    border-radius: 15px;
                    padding: 25px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    overflow-x: auto;
                }}
                table {{ 
                    width: 100%; 
                    border-collapse: collapse;
                }}
                th {{ 
                    background: #667eea; 
                    color: white; 
                    padding: 15px;
                    text-align: left;
                    font-weight: 600;
                }}
                td {{ 
                    padding: 12px 15px; 
                    border-bottom: 1px solid #eee;
                }}
                tr:hover {{ background: #f8f9fa; }}
                .priority-badge {{
                    padding: 5px 12px;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 0.85em;
                }}
                .priority-high {{ background: #ff4444; color: white; }}
                .priority-medium {{ background: #ffaa00; color: white; }}
                .priority-low {{ background: #44ff44; color: white; }}
                .status-completed {{ color: #00aa00; font-weight: bold; }}
                .live-indicator {{
                    display: inline-block;
                    width: 10px;
                    height: 10px;
                    background: #00ff00;
                    border-radius: 50%;
                    animation: pulse 2s infinite;
                    margin-right: 8px;
                }}
                @keyframes pulse {{
                    0%, 100% {{ opacity: 1; }}
                    50% {{ opacity: 0.3; }}
                }}
                .refresh-note {{
                    text-align: center;
                    color: white;
                    margin-top: 20px;
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>
                    <span class="live-indicator"></span>
                    AI Operations Command Center
                </h1>
                
                <div class="metrics">
                    <div class="metric-card">
                        <div class="metric-label">Total Signals</div>
                        <div class="metric-value">{total_signals}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Today's Signals</div>
                        <div class="metric-value">{today_signals}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Average Priority</div>
                        <div class="metric-value">{avg_priority:.1f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">High Priority (8+)</div>
                        <div class="metric-value">{high_priority}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Success Rate</div>
                        <div class="metric-value">{success_rate:.0f}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Total Actions</div>
                        <div class="metric-value">{total_executions}</div>
                    </div>
                </div>
                
                <div class="signals-table">
                    <h2 style="margin-bottom: 20px; color: #667eea;">Recent Signals</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Subject</th>
                                <th>Source</th>
                                <th>Priority</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join([f'''
                            <tr>
                                <td>{signal.detected_at.strftime('%H:%M:%S')}</td>
                                <td>{signal.subject[:50]}...</td>
                                <td>{signal.source}</td>
                                <td>
                                    <span class="priority-badge priority-{'high' if signal.priority_score >= 8 else 'medium' if signal.priority_score >= 5 else 'low'}">
                                        {signal.priority_score}/10
                                    </span>
                                </td>
                                <td class="status-{signal.status}">{signal.status}</td>
                            </tr>
                            ''' for signal in recent])}
                        </tbody>
                    </table>
                </div>
                
                <div class="refresh-note">
                    ⚡ Auto-refreshing every 5 seconds | Last updated: {datetime.now().strftime('%H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html)
        
    finally:
        db.close()
