"""Notifier module for message formatting and Telegram notifications."""

import os
import json
import logging
from typing import Dict, List
import httpx

logger = logging.getLogger(__name__)


def format_message(schedule_data: Dict[str, Dict[str, List[str]]]) -> str:
    """
    Format movie schedule data into a human-readable Telegram message.
    
    Args:
        schedule_data: Dictionary containing movie schedule information
        
    Returns:
        Formatted message string
    """
    if not schedule_data:
        return "🎬 No movies found for this week."
    
    message_lines = ["🎬 *Astor Grand Cinema - OV Schedule*\n"]
    
    for date, movies in sorted(schedule_data.items()):
        message_lines.append(f"📅 *{date}*")
        
        for title, showtimes in sorted(movies.items()):
            showtimes_str = "\n  • ".join(showtimes)
            message_lines.append(f"🎭 *{title}*")
            message_lines.append(f"  • {showtimes_str}")
        
        message_lines.append("")  # Empty line between dates
    
    message = "\n".join(message_lines).strip()
    
    # Ensure message doesn't exceed Telegram limits
    if len(message) > 4096:
        # Truncate message if too long
        message = message[:4093] + "..."
    
    return message


def send_telegram(message: str) -> bool:
    """
    Send message via Telegram Bot API.
    
    Args:
        message: Message to send
        
    Returns:
        True if successful, False otherwise
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(url, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {result}")
                return False

    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def save_to_file(message: str, schedule_data: Dict[str, Dict[str, List[str]]], output_dir: str = "output") -> None:
    """
    Save message and schedule data to local files for development testing.
    
    Args:
        message: Formatted message string
        schedule_data: Raw schedule data
        output_dir: Output directory path
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save formatted message
        message_file = os.path.join(output_dir, "latest_message.txt")
        with open(message_file, 'w', encoding='utf-8') as f:
            f.write(message)
        
        # Save raw schedule data as JSON
        json_file = os.path.join(output_dir, "schedule.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(schedule_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {output_dir}/")
        
    except Exception as e:
        logger.error(f"Failed to save results: {e}")


def notify(schedule_data: Dict[str, Dict[str, List[str]]], local_only: bool = False) -> bool:
    """
    Send notification via Telegram or save locally for development.
    
    Args:
        schedule_data: Movie schedule data
        local_only: If True, save to files instead of sending to Telegram
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Format message
        message = format_message(schedule_data)
        
        if local_only:
            # Save to local files for development testing
            save_to_file(message, schedule_data)
            logger.info("Results saved locally (development mode)")
            return True
        else:
            # Send via Telegram
            success = send_telegram(message)
            if success:
                # Also save a backup
                save_to_file(message, schedule_data, "backup")
            return success
    
    except Exception as e:
        logger.error(f"Notification failed: {e}")
        return False
