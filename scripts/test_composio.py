"""
Test script to verify Composio Tool Router setup
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.composio_client import composio_orchestrator
from src.config.logging_config import logger


def test_composio_connection():
    """Test Composio connection"""
    try:
        logger.info("Testing Composio Tool Router connection...")
        tools = composio_orchestrator.get_available_tools()
        logger.info(f"✓ Connected to Composio successfully")
        logger.info(f"Available tools: {len(tools)}")
        return True
    except Exception as e:
        logger.error(f"✗ Composio connection failed: {str(e)}")
        return False


def test_gmail_search():
    """Test Gmail search functionality"""
    try:
        logger.info("Testing Gmail search...")
        result = composio_orchestrator.execute_gmail_action(
            'search_emails',
            {'query': 'is:unread', 'maxResults': 5}
        )
        logger.info(f"✓ Gmail search successful")
        logger.info(f"Found {len(result.get('messages', []))} messages")
        return True
    except Exception as e:
        logger.error(f"✗ Gmail search failed: {str(e)}")
        return False


def main():
    """Run all tests"""
    logger.info("=" * 80)
    logger.info("Composio Tool Router Test Suite")
    logger.info("=" * 80)
    
    tests = [
        ("Composio Connection", test_composio_connection),
        ("Gmail Search", test_gmail_search)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\nRunning: {test_name}")
        logger.info("-" * 80)
        success = test_func()
        results.append((test_name, success))
        logger.info("")
    
    logger.info("=" * 80)
    logger.info("Test Results Summary")
    logger.info("=" * 80)
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
