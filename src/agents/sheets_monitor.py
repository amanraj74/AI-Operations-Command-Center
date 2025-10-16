"""
Google Sheets Monitor Agent - Monitors sheets for operational data signals
"""
from typing import List, Dict
from datetime import datetime
import asyncio

from src.config.settings import settings
from src.config.logging_config import logger
from src.utils.composio_client import composio_orchestrator


class SheetsMonitorAgent:
    """Monitors Google Sheets for operational signals"""
    
    def __init__(self):
        self.spreadsheet_id = settings.sheets_spreadsheet_id
        logger.info("SheetsMonitorAgent initialized")
    
    async def monitor_sheets(self) -> List[Dict]:
        """
        Monitor Google Sheets for signals (overdue tasks, inventory alerts, etc.)
        
        Returns:
            List of signal dictionaries
        """
        try:
            logger.info("Checking Google Sheets for operational signals")
            
            # Read data from sheets
            read_params = {
                'spreadsheetId': self.spreadsheet_id,
                'ranges': ['Operations!A1:F100', 'Tasks!A1:E50']
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                composio_orchestrator.execute_sheets_action,
                'read_range',
                read_params
            )
            
            signals = []
            
            # Process operations sheet
            if 'valueRanges' in result and len(result['valueRanges']) > 0:
                operations_data = result['valueRanges'][0].get('values', [])
                operations_signals = self._process_operations_sheet(operations_data)
                signals.extend(operations_signals)
            
            # Process tasks sheet
            if 'valueRanges' in result and len(result['valueRanges']) > 1:
                tasks_data = result['valueRanges'][1].get('values', [])
                tasks_signals = self._process_tasks_sheet(tasks_data)
                signals.extend(tasks_signals)
            
            logger.info(f"Found {len(signals)} signals from Google Sheets")
            return signals
            
        except Exception as e:
            logger.error(f"Error monitoring Google Sheets: {str(e)}")
            return []
    
    def _process_operations_sheet(self, data: List[List]) -> List[Dict]:
        """Process operations sheet data"""
        signals = []
        
        if not data or len(data) < 2:
            return signals
        
        # Skip header row
        headers = data[0]
        rows = data[1:]
        
        for idx, row in enumerate(rows):
            if len(row) < 3:
                continue
            
            # Example: Check for overdue items
            # Assuming columns: [Task, Owner, Due Date, Status, Priority, Notes]
            task = row[0] if len(row) > 0 else ''
            owner = row[1] if len(row) > 1 else ''
            due_date = row[2] if len(row) > 2 else ''
            status = row[3] if len(row) > 3 else ''
            
            # Check if overdue
            if due_date and status.lower() != 'completed':
                try:
                    due = datetime.strptime(due_date, '%Y-%m-%d')
                    if due < datetime.utcnow() and status.lower() != 'completed':
                        signal = {
                            'source': 'sheets',
                            'type': 'deadline',
                            'subject': f'Overdue Task: {task}',
                            'content': f'Task "{task}" assigned to {owner} was due on {due_date} and is still {status}',
                            'sender': 'Google Sheets Monitor',
                            'metadata': {
                                'sheet': 'Operations',
                                'row': idx + 2,
                                'task': task,
                                'owner': owner,
                                'due_date': due_date,
                                'status': status
                            }
                        }
                        signals.append(signal)
                except:
                    pass
        
        return signals
    
    def _process_tasks_sheet(self, data: List[List]) -> List[Dict]:
        """Process tasks sheet data"""
        signals = []
        
        if not data or len(data) < 2:
            return signals
        
        # Skip header row
        rows = data[1:]
        
        for idx, row in enumerate(rows):
            if len(row) < 3:
                continue
            
            # Example: Check for high-priority incomplete tasks
            # Assuming columns: [Task, Status, Priority, Assigned To, Notes]
            task = row[0] if len(row) > 0 else ''
            status = row[1] if len(row) > 1 else ''
            priority = row[2] if len(row) > 2 else ''
            
            if priority.lower() in ['high', 'critical'] and status.lower() not in ['completed', 'done']:
                signal = {
                    'source': 'sheets',
                    'type': 'high_priority_task',
                    'subject': f'High Priority Task: {task}',
                    'content': f'Task "{task}" has {priority} priority and status is {status}',
                    'sender': 'Google Sheets Monitor',
                    'metadata': {
                        'sheet': 'Tasks',
                        'row': idx + 2,
                        'task': task,
                        'status': status,
                        'priority': priority
                    }
                }
                signals.append(signal)
        
        return signals


# Global monitor instance
sheets_monitor = SheetsMonitorAgent()
