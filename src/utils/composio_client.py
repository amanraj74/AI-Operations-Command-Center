"""
Composio Tool Router client for multi-tool orchestration - v3 Compatible
"""
from composio import Composio
from openai import OpenAI
from typing import Dict, List, Any, Optional
import json
from tenacity import retry, stop_after_attempt, wait_exponential
from src.config.settings import settings
from src.config.logging_config import logger


class ComposioOrchestrator:
    """Orchestrates actions across multiple tools using Composio v3"""
    
    def __init__(self):
        try:
            self.composio_client = Composio(api_key=settings.composio_api_key)
            self.openai_client = OpenAI(api_key=settings.openai_api_key)
            self.entity_id = "default"
            logger.info("Composio Orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Composio: {str(e)}")
            self.composio_client = None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def execute_gmail_action(self, action: str, params: Dict) -> Dict:
        """Execute Gmail action through Composio v3"""
        try:
            if not self.composio_client:
                logger.warning("Composio client not initialized, using mock response")
                return self._mock_response('gmail', action, params)
            
            logger.info(f"Executing Gmail action: {action}")
            
            # Use app and action name strings
            result = self.composio_client.execute_action(
                action=f"GMAIL_{action.upper()}",
                params=params,
                entity_id=self.entity_id
            )
            
            logger.info(f"Gmail action completed: {action}")
            return result.get('data', {}) if isinstance(result, dict) else {}
            
        except Exception as e:
            logger.error(f"Gmail action failed: {action} - {str(e)}")
            return self._mock_response('gmail', action, params)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def execute_slack_action(self, action: str, params: Dict) -> Dict:
        """Execute Slack action through Composio v3"""
        try:
            if not self.composio_client:
                logger.warning("Composio client not initialized, using mock response")
                return self._mock_response('slack', action, params)
            
            logger.info(f"Executing Slack action: {action}")
            
            result = self.composio_client.execute_action(
                action=f"SLACK_{action.upper()}",
                params=params,
                entity_id=self.entity_id
            )
            
            logger.info(f"Slack action completed: {action}")
            return result.get('data', {}) if isinstance(result, dict) else {}
            
        except Exception as e:
            logger.error(f"Slack action failed: {action} - {str(e)}")
            return self._mock_response('slack', action, params)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def execute_trello_action(self, action: str, params: Dict) -> Dict:
        """Execute Trello action through Composio v3"""
        try:
            if not self.composio_client:
                logger.warning("Composio client not initialized, using mock response")
                return self._mock_response('trello', action, params)
            
            logger.info(f"Executing Trello action: {action}")
            
            result = self.composio_client.execute_action(
                action=f"TRELLO_{action.upper()}",
                params=params,
                entity_id=self.entity_id
            )
            
            logger.info(f"Trello action completed: {action}")
            return result.get('data', {}) if isinstance(result, dict) else {}
            
        except Exception as e:
            logger.error(f"Trello action failed: {action} - {str(e)}")
            return self._mock_response('trello', action, params)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def execute_notion_action(self, action: str, params: Dict) -> Dict:
        """Execute Notion action through Composio v3"""
        try:
            if not self.composio_client:
                logger.warning("Composio client not initialized, using mock response")
                return self._mock_response('notion', action, params)
            
            logger.info(f"Executing Notion action: {action}")
            
            result = self.composio_client.execute_action(
                action=f"NOTION_{action.upper()}",
                params=params,
                entity_id=self.entity_id
            )
            
            logger.info(f"Notion action completed: {action}")
            return result.get('data', {}) if isinstance(result, dict) else {}
            
        except Exception as e:
            logger.error(f"Notion action failed: {action} - {str(e)}")
            return self._mock_response('notion', action, params)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def execute_sheets_action(self, action: str, params: Dict) -> Dict:
        """Execute Google Sheets action through Composio v3"""
        try:
            if not self.composio_client:
                logger.warning("Composio client not initialized, using mock response")
                return self._mock_response('sheets', action, params)
            
            logger.info(f"Executing Sheets action: {action}")
            
            result = self.composio_client.execute_action(
                action=f"GOOGLESHEETS_{action.upper()}",
                params=params,
                entity_id=self.entity_id
            )
            
            logger.info(f"Sheets action completed: {action}")
            return result.get('data', {}) if isinstance(result, dict) else {}
            
        except Exception as e:
            logger.error(f"Sheets action failed: {action} - {str(e)}")
            return self._mock_response('sheets', action, params)
    
    def get_available_tools(self) -> List[Dict]:
        """Get list of available apps"""
        try:
            if not self.composio_client:
                return []
            apps = self.composio_client.apps.list()
            return apps if apps else []
        except Exception as e:
            logger.error(f"Failed to get available tools: {str(e)}")
            return []
    
    def _mock_response(self, tool: str, action: str, params: Dict) -> Dict:
        """Generate mock response for demo/fallback"""
        import uuid
        from datetime import datetime
        
        logger.info(f"✓ MOCK: {tool}.{action} executed successfully")
        
        response = {
            'id': f"mock_{tool}_{uuid.uuid4().hex[:8]}",
            'success': True,
            'tool': tool,
            'action': action,
            'timestamp': datetime.utcnow().isoformat(),
            'mock': True
        }
        
        # Add tool-specific fields
        if tool == 'trello':
            response['url'] = f"https://trello.com/c/{response['id']}"
        elif tool == 'notion':
            response['url'] = f"https://notion.so/{response['id']}"
        elif tool == 'slack':
            response['ts'] = response['id']
            response['channel'] = params.get('channel', 'demo_channel')
        
        return response


# Global orchestrator instance
composio_orchestrator = ComposioOrchestrator()
