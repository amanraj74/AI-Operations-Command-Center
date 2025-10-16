"""
Configuration settings for AI Operations Command Center
Loads environment variables and validates configuration
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., env='OPENAI_API_KEY')
    openai_model: str = Field(default='gpt-4-turbo-preview', env='OPENAI_MODEL')
    
    # Composio Configuration
    composio_api_key: str = Field(..., env='COMPOSIO_API_KEY')
    
    # Gmail Configuration
    gmail_client_id: str = Field(..., env='GMAIL_CLIENT_ID')
    gmail_client_secret: str = Field(..., env='GMAIL_CLIENT_SECRET')
    gmail_refresh_token: str = Field(..., env='GMAIL_REFRESH_TOKEN')
    
    # Slack Configuration
    slack_bot_token: str = Field(..., env='SLACK_BOT_TOKEN')
    slack_signing_secret: str = Field(..., env='SLACK_SIGNING_SECRET')
    slack_channel_id: str = Field(..., env='SLACK_CHANNEL_ID')
    
    # Google Sheets Configuration
    sheets_spreadsheet_id: str = Field(..., env='SHEETS_SPREADSHEET_ID')
    
    # Notion Configuration
    notion_token: str = Field(..., env='NOTION_TOKEN')
    notion_database_id: str = Field(..., env='NOTION_DATABASE_ID')
    
    # Trello Configuration
    trello_api_key: str = Field(..., env='TRELLO_API_KEY')
    trello_token: str = Field(..., env='TRELLO_TOKEN')
    trello_board_id: str = Field(..., env='TRELLO_BOARD_ID')
    
    # Google Drive Configuration
    drive_folder_id: str = Field(..., env='DRIVE_FOLDER_ID')
    
    # Database Configuration
    database_url: str = Field(..., env='DATABASE_URL')
    
    # Server Configuration
    host: str = Field(default='0.0.0.0', env='HOST')
    port: int = Field(default=8000, env='PORT')
    debug: bool = Field(default=False, env='DEBUG')
    
    # Agent Configuration
    priority_threshold: int = Field(default=7, env='PRIORITY_THRESHOLD', ge=1, le=10)
    max_retries: int = Field(default=3, env='MAX_RETRIES', ge=1, le=10)
    webhook_timeout: int = Field(default=30, env='WEBHOOK_TIMEOUT', ge=10, le=300)
    
    # Application Metadata
    app_name: str = "AI Operations Command Center"
    app_version: str = "1.0.0"
    
    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    logs_dir: Path = base_dir / "logs"
    data_dir: Path = base_dir / "data"
    
    @validator('logs_dir', 'data_dir')
    def create_directories(cls, v):
        """Ensure directories exist"""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
