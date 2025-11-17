"""Main orchestration module for KinoWeek scraper."""

import logging
import os
import sys
from typing import Dict, List

from .scraper import scrape_movies
from .notifier import notify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('kinoweek.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def validate_environment(local_only: bool) -> None:
    """
    Validate required environment variables at startup.

    Fails fast if environment variables are missing when sending to Telegram.

    Args:
        local_only: If True, skip validation (running in local test mode)

    Raises:
        SystemExit: If required environment variables are missing
    """
    if local_only:
        return

    missing = []
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        missing.append("TELEGRAM_BOT_TOKEN")
    if not os.getenv("TELEGRAM_CHAT_ID"):
        missing.append("TELEGRAM_CHAT_ID")

    if missing:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing)}")
        logger.error("Set these in .env file or export them before running")
        sys.exit(1)


def run_scraper(local_only: bool = False) -> bool:
    """
    Run the complete scraping and notification workflow.

    Args:
        local_only: If True, save results locally instead of sending to Telegram

    Returns:
        True if successful, False otherwise
    """
    # Validate environment before proceeding
    validate_environment(local_only)

    try:
        logger.info("🚀 Starting Astor Kino scraper")
        
        # Step 1: Scrape movie data
        logger.info("📡 Scraping movie schedules...")
        schedule_data = scrape_movies()
        
        if not schedule_data:
            logger.warning("⚠️  No movie data found")
            # Create empty data for notification
            schedule_data = {}
        
        logger.info(f"📊 Found data for {len(schedule_data)} dates")
        
        # Step 2: Send notification or save locally
        logger.info("📨 Sending notification...")
        success = notify(schedule_data, local_only=local_only)
        
        if success:
            logger.info("✅ Workflow completed successfully")
            return True
        else:
            logger.error("❌ Failed to send notification")
            return False
    
    except Exception as e:
        logger.error(f"💥 Workflow failed: {e}")
        return False


def main() -> int:
    """
    Main entry point for the application.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Astor Kino Scraper")
    parser.add_argument(
        "--local", 
        action="store_true", 
        help="Save results locally instead of sending to Telegram"
    )
    
    args = parser.parse_args()
    
    success = run_scraper(local_only=args.local)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
