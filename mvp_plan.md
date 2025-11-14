# MVP Plan: Astor Kino Notifier (KinoWeek)

## Goal
Create the simplest working version that tests the core scraping logic and Telegram notification.

## MVP Components

### 1. Core Scraper (`scrape_movies.py`)
```python
# Simple functions:
- scrape_movies() -> dict
- format_message(data) -> str  
- send_telegram(message) -> bool
```

### 2. Data Structure
```python
{
    "Mon 24.11": {
        "Wicked: Part 2": ["19:30 (Cinema 10, 2D OV)"]
    }
}
```

### 3. Environment Variables
```
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

### 4. Basic Files
- `scrape_movies.py` (main script)
- `requirements.txt` (playwright, requests)
- `.env.example` (env var template)
- `.gitignore` (already exists)

## MVP Workflow
1. Launch Playwright browser
2. Navigate to cinema website
3. Click date tabs, extract movies/showtimes
4. Format as simple text message
5. Send via Telegram
6. Save JSON backup

## Success Criteria
- Script runs without errors
- Extracts real movie data
- Sends Telegram message
- Completes within 5 minutes

## Next Steps After MVP
1. Add error handling
2. Create Docker container
3. Deploy to Coolify
4. Set up weekly schedule
