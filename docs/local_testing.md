
1. **Install Dependencies**
   ```bash
   # Install all dependencies from uv.lock
   uv sync --dev
   ```

2. **Set Up Environment Variables** (Optional for local testing)
   ```bash
   # Copy the template
   cp .env.example .env

   # Edit .env with your Telegram credentials (only needed for Telegram testing)
   # TELEGRAM_BOT_TOKEN=your_bot_token_here
   # TELEGRAM_CHAT_ID=your_chat_id_here
   ```

## Local Testing

### Quick Test (No Telegram)
```bash
# Test locally - saves results to output/ folder
PYTHONPATH=src uv run python -m kinoweek.main --local
```

## Running Tests

```bash
# Install package in editable mode
uv pip install -e .

# Run all tests
uv run pytest tests/ -v

# Run specific test class
uv run pytest tests/test_scraper.py::TestScrapeMovies -v

# Run with coverage
uv run pytest tests/ -v --cov=kinoweek
```