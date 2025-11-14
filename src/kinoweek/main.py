"""Main orchestration module for KinoWeek scraper."""

import logging
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


def run_scraper(local_only: bool = False) -> bool:
    """
    Run the complete scraping and notification workflow.
    
    Args:
        local_only: If True, save results locally instead of sending to Telegram
        
    Returns:
        True if successful, False otherwise
    """
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
