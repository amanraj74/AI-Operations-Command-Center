"""
Main application entry point
Starts the FastAPI server and monitoring system
"""
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import settings
from src.config.logging_config import logger
from src.webhooks.api_server import app
import uvicorn


def main():
    """Main entry point"""
    logger.info("=" * 80)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info("=" * 80)
    logger.info(f"Host: {settings.host}")
    logger.info(f"Port: {settings.port}")
    logger.info(f"Debug Mode: {settings.debug}")
    logger.info(f"Priority Threshold: {settings.priority_threshold}")
    logger.info("=" * 80)
    
    try:
        # Start FastAPI server with uvicorn
        uvicorn.run(
            "src.webhooks.api_server:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        sys.exit(1)
    finally:
        logger.info("Application stopped")


if __name__ == "__main__":
    main()
