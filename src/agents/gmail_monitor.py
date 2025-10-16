"""
Gmail Monitor Agent - Monitors Gmail for urgent emails and customer complaints
"""
from typing import List, Dict
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.config.logging_config import logger
from src.utils.composio_client import composio_orchestrator


class GmailMonitorAgent:
    """Monitors Gmail inbox for operational signals"""
    
    def __init__(self):
        self.check_interval = 60  # Check every 60 seconds
        self.lookback_minutes = 5  # Look back 5 minutes
        logger.info("GmailMonitorAgent initialized")
    
    async def monitor_inbox(self) -> List[Dict]:
        """
        Monitor Gmail inbox for new high-priority emails
        
        Returns:
            List of signal dictionaries
        """
        try:
            logger.info("Checking Gmail inbox for new signals")
            
            # Calculate time range
            after_date = datetime.utcnow() - timedelta(minutes=self.lookback_minutes)
            date_str = after_date.strftime('%Y/%m/%d')
            
            # Search for unread emails from last N minutes
            search_params = {
                'query': f'is:unread after:{date_str}',
                'maxResults': 50
            }
            
            # Execute search through Composio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                composio_orchestrator.execute_gmail_action,
                'search_emails',
                search_params
            )
            
            emails = result.get('messages', [])
            logger.info(f"Found {len(emails)} unread emails")
            
            # Process each email
            signals = []
            for email_data in emails[:10]:  # Process max 10 at a time
                signal = await self._process_email(email_data)
                if signal:
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error monitoring Gmail: {str(e)}")
            return []
    
    async def _process_email(self, email_data: Dict) -> Dict:
        """Process individual email and create signal"""
        try:
            email_id = email_data.get('id')
            
            # Get full email details
            loop = asyncio.get_event_loop()
            email_details = await loop.run_in_executor(
                None,
                composio_orchestrator.execute_gmail_action,
                'get_email',
                {'id': email_id}
            )
            
            # Extract email information
            headers = {h['name']: h['value'] for h in email_details.get('payload', {}).get('headers', [])}
            subject = headers.get('Subject', 'No Subject')
            sender = headers.get('From', 'Unknown')
            date = headers.get('Date', '')
            
            # Get email body
            body = self._extract_email_body(email_details.get('payload', {}))
            
            # Determine signal type based on content analysis
            signal_type = self._classify_email(subject, body, sender)
            
            signal = {
                'source': 'gmail',
                'type': signal_type,
                'subject': subject,
                'content': body[:5000],
                'sender': sender,
                'metadata': {
                    'email_id': email_id,
                    'date': date,
                    'labels': email_details.get('labelIds', [])
                }
            }
            
            logger.info(f"Processed email signal: {signal_type} from {sender}")
            return signal
            
        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            return None
    
    def _extract_email_body(self, payload: Dict) -> str:
        """Extract text from email payload"""
        try:
            if 'body' in payload and payload['body'].get('data'):
                import base64
                body_data = payload['body']['data']
                body_bytes = base64.urlsafe_b64decode(body_data)
                return body_bytes.decode('utf-8', errors='ignore')
            
            # Check parts for multipart emails
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        if part.get('body', {}).get('data'):
                            import base64
                            body_data = part['body']['data']
                            body_bytes = base64.urlsafe_b64decode(body_data)
                            return body_bytes.decode('utf-8', errors='ignore')
            
            return "Email body could not be extracted"
            
        except Exception as e:
            logger.error(f"Error extracting email body: {str(e)}")
            return ""
    
    def _classify_email(self, subject: str, body: str, sender: str) -> str:
        """Classify email type based on content"""
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        # Customer complaint indicators
        complaint_keywords = ['complaint', 'issue', 'problem', 'dissatisfied', 'disappointed', 'terrible', 'awful']
        if any(keyword in subject_lower or keyword in body_lower for keyword in complaint_keywords):
            return 'customer_complaint'
        
        # Urgent indicators
        urgent_keywords = ['urgent', 'asap', 'immediate', 'critical', 'emergency']
        if any(keyword in subject_lower for keyword in urgent_keywords):
            return 'urgent_email'
        
        # Deadline indicators
        deadline_keywords = ['deadline', 'due date', 'overdue', 'expired']
        if any(keyword in subject_lower or keyword in body_lower for keyword in deadline_keywords):
            return 'deadline'
        
        # System alerts
        if 'noreply' in sender.lower() or 'alert' in subject_lower:
            return 'system_alert'
        
        return 'general_email'


# Global monitor instance
gmail_monitor = GmailMonitorAgent()
