"""
Main Orchestration Agent - Coordinates all operations
Monitors signals, prioritizes, and orchestrates tasks across tools
"""
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import uuid
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.config.logging_config import logger
from src.models.database import OperationalSignal, TaskExecution, get_db
from src.utils.priority_analyzer import priority_analyzer
from src.utils.composio_client import composio_orchestrator


class OrchestratorAgent:
    """
    Main orchestration agent that:
    1. Monitors incoming signals from Gmail, Slack, Sheets
    2. Analyzes priority using AI
    3. Orchestrates actions across Trello, Notion, Slack, Drive
    """
    
    def __init__(self):
        self.priority_threshold = settings.priority_threshold
        self.max_retries = settings.max_retries
        logger.info("OrchestratorAgent initialized")
    
    async def process_signal(self, signal_data: Dict, db: Session) -> Dict:
        """
        Main entry point: Process incoming operational signal
        
        Args:
            signal_data: Dictionary with signal information
            db: Database session
            
        Returns:
            Processing result dictionary
        """
        signal_id = str(uuid.uuid4())
        logger.info(f"Processing signal: {signal_id} from {signal_data.get('source')}")
        
        try:
            # Step 1: Store initial signal
            signal = self._create_signal_record(signal_id, signal_data, db)
            
            # Step 2: Analyze priority using AI
            priority_score, summary, reasoning, recommended_action = await self._analyze_priority(signal_data)
            
            # Step 3: Update signal with AI analysis
            signal.priority_score = priority_score
            signal.ai_summary = summary
            signal.ai_reasoning = reasoning
            signal.recommended_action = recommended_action
            signal.status = 'processing'
            db.commit()
            
            logger.info(f"Signal {signal_id} analyzed: priority={priority_score}")
            
            # Step 4: Check if priority meets threshold
            if priority_score < self.priority_threshold:
                logger.info(f"Signal {signal_id} below threshold ({priority_score} < {self.priority_threshold}), skipping orchestration")
                signal.status = 'completed'
                signal.completed_at = datetime.utcnow()
                db.commit()
                
                return {
                    'signal_id': signal_id,
                    'status': 'low_priority',
                    'priority_score': priority_score,
                    'message': 'Signal below priority threshold'
                }
            
            # Step 5: Orchestrate actions across tools
            orchestration_result = await self._orchestrate_actions(signal, db)
            
            # Step 6: Update signal status
            signal.status = 'completed' if orchestration_result['success'] else 'failed'
            signal.completed_at = datetime.utcnow()
            signal.processed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Signal {signal_id} processing complete: {signal.status}")
            
            return {
                'signal_id': signal_id,
                'status': signal.status,
                'priority_score': priority_score,
                'orchestration': orchestration_result,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error processing signal {signal_id}: {str(e)}")
            
            # Update signal with error
            if 'signal' in locals():
                signal.status = 'failed'
                signal.error_message = str(e)
                signal.retries += 1
                db.commit()
            
            return {
                'signal_id': signal_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _create_signal_record(self, signal_id: str, signal_data: Dict, db: Session) -> OperationalSignal:
        """Create initial signal record in database"""
        signal = OperationalSignal(
            signal_id=signal_id,
            source=signal_data.get('source', 'unknown'),
            signal_type=signal_data.get('type', 'unknown'),
            priority_score=0.0,
            status='pending',
            subject=signal_data.get('subject', '')[:500],
            description=signal_data.get('content', '')[:5000],
            sender=signal_data.get('sender', ''),
            raw_data=str(signal_data),
            detected_at=datetime.utcnow()
        )
        
        db.add(signal)
        db.commit()
        db.refresh(signal)
        
        return signal
    
    async def _analyze_priority(self, signal_data: Dict) -> tuple:
        """Analyze signal priority using AI"""
        try:
            # Run priority analysis in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                priority_analyzer.analyze_signal,
                signal_data
            )
            return result
        except Exception as e:
            logger.error(f"Priority analysis failed: {str(e)}")
            return 5.0, "Analysis failed", str(e), "Manual review required"
    
    async def _orchestrate_actions(self, signal: OperationalSignal, db: Session) -> Dict:
        """
        Orchestrate actions across multiple tools based on signal priority
        
        Workflow:
        1. Create Trello card for task tracking
        2. Update Notion dashboard
        3. Post alert to Slack
        4. Assign team member (if applicable)
        """
        results = {
            'success': True,
            'actions': []
        }
        
        try:
            # Action 1: Create Trello Card
            trello_result = await self._create_trello_card(signal, db)
            results['actions'].append(trello_result)
            
            if trello_result['success']:
                signal.trello_card_id = trello_result.get('card_id')
            
            # Action 2: Create Notion Page
            notion_result = await self._create_notion_page(signal, db)
            results['actions'].append(notion_result)
            
            if notion_result['success']:
                signal.notion_page_id = notion_result.get('page_id')
            
            # Action 3: Post to Slack
            slack_result = await self._post_slack_alert(signal, db)
            results['actions'].append(slack_result)
            
            if slack_result['success']:
                signal.slack_message_id = slack_result.get('message_id')
            
            # Action 4: Assign team member (based on signal type)
            assignment_result = await self._assign_team_member(signal, db)
            results['actions'].append(assignment_result)
            
            if assignment_result['success']:
                signal.assigned_to = assignment_result.get('assigned_to')
            
            # Check if all critical actions succeeded
            critical_actions = [trello_result, notion_result, slack_result]
            results['success'] = all(action['success'] for action in critical_actions)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Orchestration failed for signal {signal.signal_id}: {str(e)}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    async def _create_trello_card(self, signal: OperationalSignal, db: Session) -> Dict:
        """Create Trello card for task tracking"""
        execution = TaskExecution(
            signal_id=signal.signal_id,
            tool_name='trello',
            action='create_card',
            status='pending',
            started_at=datetime.utcnow()
        )
        db.add(execution)
        db.commit()
        
        try:
            # Determine list based on priority
            list_name = self._get_trello_list_for_priority(signal.priority_score)
            
            # Create card parameters
            card_params = {
                'name': f"[P{int(signal.priority_score)}] {signal.subject}",
                'desc': f"""**Priority:** {signal.priority_score}/10

**Source:** {signal.source}
**From:** {signal.sender}
**Detected:** {signal.detected_at.strftime('%Y-%m-%d %H:%M')}

**AI Summary:**
{signal.ai_summary}

**Reasoning:**
{signal.ai_reasoning}

**Recommended Action:**
{signal.recommended_action}

**Details:**
{signal.description[:1000]}
""",
                'idList': self._get_trello_list_id(list_name),
                'pos': 'top'
            }
            
            # Execute through Composio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                composio_orchestrator.execute_trello_action,
                'create_card',
                card_params
            )
            
            execution.status = 'success'
            execution.completed_at = datetime.utcnow()
            execution.response_data = str(result)
            db.commit()
            
            logger.info(f"Trello card created for signal {signal.signal_id}")
            
            return {
                'success': True,
                'tool': 'trello',
                'action': 'create_card',
                'card_id': result.get('id'),
                'card_url': result.get('url')
            }
            
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            db.commit()
            
            logger.error(f"Failed to create Trello card: {str(e)}")
            
            return {
                'success': False,
                'tool': 'trello',
                'action': 'create_card',
                'error': str(e)
            }
    
    async def _create_notion_page(self, signal: OperationalSignal, db: Session) -> Dict:
        """Create Notion page in operations dashboard"""
        execution = TaskExecution(
            signal_id=signal.signal_id,
            tool_name='notion',
            action='create_page',
            status='pending',
            started_at=datetime.utcnow()
        )
        db.add(execution)
        db.commit()
        
        try:
            # Create page parameters
            page_params = {
                'parent': {'database_id': settings.notion_database_id},
                'properties': {
                    'Name': {
                        'title': [
                            {
                                'text': {
                                    'content': signal.subject[:100]
                                }
                            }
                        ]
                    },
                    'Priority': {
                        'number': signal.priority_score
                    },
                    'Status': {
                        'select': {
                            'name': 'In Progress'
                        }
                    },
                    'Source': {
                        'select': {
                            'name': signal.source.capitalize()
                        }
                    },
                    'Assigned': {
                        'rich_text': [
                            {
                                'text': {
                                    'content': signal.assigned_to or 'Unassigned'
                                }
                            }
                        ]
                    }
                },
                'children': [
                    {
                        'object': 'block',
                        'type': 'heading_2',
                        'heading_2': {
                            'rich_text': [{'type': 'text', 'text': {'content': 'AI Analysis'}}]
                        }
                    },
                    {
                        'object': 'block',
                        'type': 'paragraph',
                        'paragraph': {
                            'rich_text': [{'type': 'text', 'text': {'content': signal.ai_summary}}]
                        }
                    },
                    {
                        'object': 'block',
                        'type': 'heading_2',
                        'heading_2': {
                            'rich_text': [{'type': 'text', 'text': {'content': 'Recommended Action'}}]
                        }
                    },
                    {
                        'object': 'block',
                        'type': 'paragraph',
                        'paragraph': {
                            'rich_text': [{'type': 'text', 'text': {'content': signal.recommended_action}}]
                        }
                    }
                ]
            }
            
            # Execute through Composio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                composio_orchestrator.execute_notion_action,
                'create_page',
                page_params
            )
            
            execution.status = 'success'
            execution.completed_at = datetime.utcnow()
            execution.response_data = str(result)
            db.commit()
            
            logger.info(f"Notion page created for signal {signal.signal_id}")
            
            return {
                'success': True,
                'tool': 'notion',
                'action': 'create_page',
                'page_id': result.get('id'),
                'page_url': result.get('url')
            }
            
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            db.commit()
            
            logger.error(f"Failed to create Notion page: {str(e)}")
            
            return {
                'success': False,
                'tool': 'notion',
                'action': 'create_page',
                'error': str(e)
            }
    
    async def _post_slack_alert(self, signal: OperationalSignal, db: Session) -> Dict:
        """Post alert to Slack channel"""
        execution = TaskExecution(
            signal_id=signal.signal_id,
            tool_name='slack',
            action='send_message',
            status='pending',
            started_at=datetime.utcnow()
        )
        db.add(execution)
        db.commit()
        
        try:
            # Create Slack message with rich formatting
            priority_emoji = self._get_priority_emoji(signal.priority_score)
            
            message_params = {
                'channel': settings.slack_channel_id,
                'blocks': [
                    {
                        'type': 'header',
                        'text': {
                            'type': 'plain_text',
                            'text': f'{priority_emoji} New High-Priority Signal'
                        }
                    },
                    {
                        'type': 'section',
                        'fields': [
                            {
                                'type': 'mrkdwn',
                                'text': f'*Priority:*\n{signal.priority_score}/10'
                            },
                            {
                                'type': 'mrkdwn',
                                'text': f'*Source:*\n{signal.source.capitalize()}'
                            },
                            {
                                'type': 'mrkdwn',
                                'text': f'*From:*\n{signal.sender}'
                            },
                            {
                                'type': 'mrkdwn',
                                'text': f'*Detected:*\n{signal.detected_at.strftime("%Y-%m-%d %H:%M")}'
                            }
                        ]
                    },
                    {
                        'type': 'section',
                        'text': {
                            'type': 'mrkdwn',
                            'text': f'*Subject:*\n{signal.subject}'
                        }
                    },
                    {
                        'type': 'section',
                        'text': {
                            'type': 'mrkdwn',
                            'text': f'*AI Summary:*\n{signal.ai_summary}'
                        }
                    },
                    {
                        'type': 'section',
                        'text': {
                            'type': 'mrkdwn',
                            'text': f'*Recommended Action:*\n{signal.recommended_action}'
                        }
                    },
                    {
                        'type': 'section',
                        'text': {
                            'type': 'mrkdwn',
                            'text': f'*Assigned To:*\n{signal.assigned_to or "Unassigned"}'
                        }
                    },
                    {
                        'type': 'divider'
                    },
                    {
                        'type': 'context',
                        'elements': [
                            {
                                'type': 'mrkdwn',
                                'text': f'Signal ID: `{signal.signal_id}`'
                            }
                        ]
                    }
                ]
            }
            
            # Execute through Composio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                composio_orchestrator.execute_slack_action,
                'send_message',
                message_params
            )
            
            execution.status = 'success'
            execution.completed_at = datetime.utcnow()
            execution.response_data = str(result)
            db.commit()
            
            logger.info(f"Slack alert posted for signal {signal.signal_id}")
            
            return {
                'success': True,
                'tool': 'slack',
                'action': 'send_message',
                'message_id': result.get('ts'),
                'channel': settings.slack_channel_id
            }
            
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            db.commit()
            
            logger.error(f"Failed to post Slack alert: {str(e)}")
            
            return {
                'success': False,
                'tool': 'slack',
                'action': 'send_message',
                'error': str(e)
            }
    
    async def _assign_team_member(self, signal: OperationalSignal, db: Session) -> Dict:
        """Assign team member based on signal type and priority"""
        try:
            # Simple assignment logic (can be enhanced with AI)
            assignment_map = {
                'customer_complaint': 'support@company.com',
                'urgent_email': 'manager@company.com',
                'deadline': 'project-lead@company.com',
                'system_alert': 'devops@company.com',
                'financial': 'finance@company.com'
            }
            
            assigned_to = assignment_map.get(signal.signal_type, 'operations@company.com')
            
            logger.info(f"Signal {signal.signal_id} assigned to {assigned_to}")
            
            return {
                'success': True,
                'tool': 'assignment',
                'action': 'assign_member',
                'assigned_to': assigned_to
            }
            
        except Exception as e:
            logger.error(f"Failed to assign team member: {str(e)}")
            return {
                'success': False,
                'tool': 'assignment',
                'action': 'assign_member',
                'error': str(e)
            }
    
    def _get_trello_list_for_priority(self, priority_score: float) -> str:
        """Get Trello list name based on priority score"""
        if priority_score >= 9:
            return 'Critical'
        elif priority_score >= 7:
            return 'High Priority'
        elif priority_score >= 5:
            return 'Medium Priority'
        else:
            return 'Low Priority'
    
    def _get_trello_list_id(self, list_name: str) -> str:
        """Get Trello list ID from name (placeholder - should be configured)"""
        # In production, fetch this dynamically from Trello API
        list_mapping = {
            'Critical': settings.trello_board_id,  # Use actual list IDs
            'High Priority': settings.trello_board_id,
            'Medium Priority': settings.trello_board_id,
            'Low Priority': settings.trello_board_id
        }
        return list_mapping.get(list_name, settings.trello_board_id)
    
    def _get_priority_emoji(self, priority_score: float) -> str:
        """Get emoji for priority level"""
        if priority_score >= 9:
            return '🚨'
        elif priority_score >= 7:
            return '⚠️'
        elif priority_score >= 5:
            return '📌'
        else:
            return 'ℹ️'


# Global orchestrator instance
orchestrator_agent = OrchestratorAgent()
