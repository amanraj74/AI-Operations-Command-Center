"""
Database initialization script
Creates all tables and optionally seeds test data
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.database import Base, engine, SessionLocal
from src.config.logging_config import logger
from src.config.settings import settings


def create_tables():
    """Create all database tables"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create tables: {str(e)}")
        return False


def drop_tables():
    """Drop all database tables"""
    try:
        logger.info("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("✓ Database tables dropped successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to drop tables: {str(e)}")
        return False


def reset_database():
    """Drop and recreate all tables"""
    logger.info("Resetting database...")
    if drop_tables() and create_tables():
        logger.info("✓ Database reset successfully")
        return True
    else:
        logger.error("✗ Database reset failed")
        return False


def verify_connection():
    """Verify database connection"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info("✓ Database connection verified")
        return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {str(e)}")
        return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database initialization utility")
    parser.add_argument(
        'action',
        choices=['create', 'drop', 'reset', 'verify'],
        help='Action to perform'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Database Initialization Utility")
    logger.info("=" * 80)
    logger.info(f"Database URL: {settings.database_url}")
    logger.info("=" * 80)
    
    if args.action == 'create':
        success = create_tables()
    elif args.action == 'drop':
        confirm = input("Are you sure you want to drop all tables? (yes/no): ")
        if confirm.lower() == 'yes':
            success = drop_tables()
        else:
            logger.info("Operation cancelled")
            return
    elif args.action == 'reset':
        confirm = input("Are you sure you want to reset the database? (yes/no): ")
        if confirm.lower() == 'yes':
            success = reset_database()
        else:
            logger.info("Operation cancelled")
            return
    elif args.action == 'verify':
        success = verify_connection()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
