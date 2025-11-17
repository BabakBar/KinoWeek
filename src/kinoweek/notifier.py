"""Notifier module for message formatting and Telegram notifications."""

import os
import json
import logging
from typing import Dict, List
import httpx

logger = logging.getLogger(__name__)


def format_message(schedule_data: Dict[str, Dict[str, Dict]]) -> str:
    """
    Format movie schedule data into a human-readable Telegram message.

    Args:
        schedule_data: Dictionary containing movie schedule information with metadata

    Returns:
        Formatted message string
    """
    if not schedule_data:
        return "🎬 No movies found for this week."

    total_movies = 0
    total_showtimes = 0

    # Calculate totals first
    for date, movies in schedule_data.items():
        for title, movie_data in movies.items():
            total_movies += 1
            total_showtimes += len(movie_data['showtimes'])

    # Start with header and summary
    message_lines = [
        "🎬 *Astor Grand Cinema - OV Movies*",
        f"📊 {total_movies} films • {total_showtimes} showtimes • {len(schedule_data)} days\n"
    ]

    # Data is already sorted by date from scraper
    for date, movies in schedule_data.items():
        message_lines.append(f"📅 *{date}*")

        for title, movie_data in sorted(movies.items()):
            info = movie_data['info']
            showtimes = movie_data['showtimes']

            # Movie title with year
            title_line = f"🎬 *{info.title}*"
            if info.year:
                title_line += f" ({info.year})"
            message_lines.append(title_line)

            # Movie metadata (duration, rating) - more compact
            metadata_parts = []
            if info.duration:
                hours = info.duration // 60
                mins = info.duration % 60
                if hours > 0:
                    metadata_parts.append(f"{hours}h{mins}m" if mins else f"{hours}h")
                else:
                    metadata_parts.append(f"{mins}m")

            if info.rating:
                metadata_parts.append(f"FSK{info.rating}")

            # Showtimes - more compact format
            showtime_strs = []
            for showtime in showtimes:
                # Simplify language display
                version_display = showtime.version
                version_display = version_display.replace("Sprache: ", "")
                version_display = version_display.replace("Untertitel: ", "UT:")
                # Make even more compact
                version_display = version_display.replace("Englisch", "EN")
                version_display = version_display.replace("Japanisch", "JP")
                version_display = version_display.replace("Italienisch", "IT")
                version_display = version_display.replace("Spanisch", "ES")
                version_display = version_display.replace("Russisch", "RU")
                version_display = version_display.replace("Deutsch", "DE")

                showtime_strs.append(f"{showtime.time_str} ({version_display})")

            times_line = "  ⏰ " + " • ".join(showtime_strs)
            if metadata_parts:
                message_lines.append(f"  _{' • '.join(metadata_parts)}_")
            message_lines.append(times_line)
            message_lines.append("")  # Empty line between movies

        message_lines.append("─" * 35)  # Separator between dates

    message = "\n".join(message_lines).strip()

    # Ensure message doesn't exceed Telegram limits
    if len(message) > 4096:
        # Truncate message if too long and add note
        message = message[:4050] + "\n\n... (truncated - too many showings)"

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


def save_to_file(message: str, schedule_data: Dict[str, Dict[str, Dict]], output_dir: str = "output") -> None:
    """
    Save message and schedule data to local files for development testing.

    Args:
        message: Formatted message string
        schedule_data: Raw schedule data with movie metadata
        output_dir: Output directory path
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Save formatted message
        message_file = os.path.join(output_dir, "latest_message.txt")
        with open(message_file, 'w', encoding='utf-8') as f:
            f.write(message)

        # Convert schedule data to JSON-serializable format
        json_data = {}
        for date, movies in schedule_data.items():
            json_data[date] = {}
            for title, movie_data in movies.items():
                info = movie_data['info']
                showtimes = movie_data['showtimes']

                json_data[date][title] = {
                    'metadata': {
                        'duration': info.duration,
                        'rating': info.rating,
                        'year': info.year,
                        'country': info.country,
                        'genres': info.genres
                    },
                    'showtimes': [
                        {
                            'time': st.time_str,
                            'version': st.version,
                            'datetime': st.datetime.isoformat()
                        }
                        for st in showtimes
                    ]
                }

        # Save structured schedule data as JSON
        json_file = os.path.join(output_dir, "schedule.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to {output_dir}/")

    except Exception as e:
        logger.error(f"Failed to save results: {e}")


def notify(schedule_data: Dict[str, Dict[str, Dict]], local_only: bool = False) -> bool:
    """
    Send notification via Telegram or save locally for development.

    Args:
        schedule_data: Movie schedule data with metadata
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
