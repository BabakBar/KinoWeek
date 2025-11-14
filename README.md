# KinoWeek - Astor Kino Notifier

Automated web scraping system for Astor Grand Cinema Hannover Original Version (OV) movie schedules with Telegram notifications.

## Quick Start

```bash
# Install dependencies with uv
uv sync --dev

# Install Playwright browsers
uv run playwright install

# Set up environment variables
cp .env.example .env
# Edit .env with your Telegram bot token and chat ID

# Run the scraper
uv run python scrape_movies.py
```

## Environment Variables

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## Development

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=scrape_movies
```

## Deployment

Deploy using Coolify with scheduled tasks (weekly execution).
