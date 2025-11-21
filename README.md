# KinoWeek - Weekly Event Digest for Hannover

A stateless, weekly script that aggregates cultural events in Hannover from two curated sources and delivers a formatted digest via Telegram.

## The Lean MVP Philosophy

**Complexity kills side projects.** KinoWeek is intentionally simple:
- **No Database**: Stateless - just run it weekly
- **No Deduplication**: Simple is better than perfect
- **No Real-time Alerts**: One message per week, every Monday
- **Two Quality Sources**: High signal, low noise

## Features

- **Movies (This Week)**: OV (original version) movies at Astor Grand Cinema
- **On The Radar**: Big upcoming concerts at ZAG Arena, Swiss Life Hall, Capitol
- **Telegram Integration**: Weekly digest delivered to your phone
- **Local Testing Mode**: Test without sending messages
- **Easy Configuration**: All URLs and settings in one file

## Quick Start

```bash
# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your Telegram bot token and chat ID

# Test locally (saves to output/ directory)
uv run python -m kinoweek.main --local

# Run with Telegram notifications
uv run python -m kinoweek.main
```

## Message Format

The script generates a compact weekly digest with two sections:

```
*Hannover Week 47*

*Movies (This Week)*

*Fri 21.11.*
  *Chainsaw Man - The Movie: Reze Arc (2025)*
  _1h41m | FSK16_
  22:50 (JP, UT:DE)

*Sat 22.11.*
  *Wicked: Teil 2 (2025)*
  _2h17m | FSK12_
  13:45 (EN)
  *Wicked: Teil 2 (2025)*
  _2h17m | FSK12_
  19:50 (EN)

*On The Radar*
  *LUCIANO*
  Sa, 29. Nov | 20:00 @ ZAG Arena
  *BÖHSE ONKELZ*
  So, 30. Nov | 19:30 @ ZAG Arena
  *Architects*
  Di, 13. Jan 2026 | 20:00 @ Swiss Life Hall
```

## Architecture

### The Two Sources

1. **Astor Grand Cinema** (OV Movies)
   - Source: Direct API access to `backend.premiumkino.de`
   - Filter: Original version movies only (no German dubs)
   - Includes: EN, JP, IT, ES, RU + films with German subtitles
   - Timeframe: Next 7 days

2. **Concert Venues** (Big Events)
   - Sources: ZAG Arena, Swiss Life Hall, Capitol Hannover
   - Content: Major concerts and shows
   - Purpose: "Planning horizon" for big events
   - Timeframe: Events beyond 7 days (on the radar)

### How It Works

```
┌─────────────────┐
│   Run Weekly    │  (Monday, via cron)
│   (Stateless)   │
└────────┬────────┘
         │
         ├──► Fetch Astor Movies    ─┐
         └──► Fetch Concert Events  ─┘ Parallel
                    │
                    ▼
         ┌──────────────────┐
         │  Filter & Sort   │
         │  • This Week     │
         │  • On The Radar  │
         └────────┬─────────┘
                  │
                  ▼
         ┌────────────────┐
         │  Format Message│
         │  (2 Sections)  │
         └────────┬───────┘
                  │
                  ▼
         ┌────────────────┐
         │Send to Telegram│
         └────────────────┘
```

## Configuration

Edit `src/kinoweek/config.py` to customize:

```python
# Concert sources (enable/disable as needed)
CONCERT_VENUES = (
    {
        "name": "ZAG Arena",
        "url": "https://www.zag-arena-hannover.de/veranstaltungen/",
        "enabled": True,
        "selectors": {...}
    },
    {
        "name": "Swiss Life Hall",
        "url": "https://www.swisslife-hall.de/events/",
        "enabled": True,
        "selectors": {...}
    },
    {
        "name": "Capitol Hannover",
        "url": "https://www.capitol-hannover.de/events/",
        "enabled": True,
        "selectors": {...}
    },
)
```

## Environment Variables

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
LOG_LEVEL=INFO  # Optional
```

## Development

```bash
# Run tests
uv run python -m pytest tests/ -v

# Test the full workflow locally
uv run python -m kinoweek.main --local

# Check output files
cat output/latest_message.txt
cat output/events.json
```

## Project Structure

```
src/kinoweek/
├── __init__.py    # Package exports and lazy imports
├── models.py      # Event dataclass (unified data structure)
├── config.py      # URLs, venues, and settings
├── scrapers.py    # AstorMovieScraper + ConcertVenueScraper classes
├── notifier.py    # Message formatting + Telegram API
└── main.py        # Orchestration + CLI

tests/
└── test_scraper.py  # 26 unit and integration tests

output/
├── latest_message.txt  # Formatted message
└── events.json         # Structured event data
```

## Deployment

### Weekly Cron Job

```bash
# Run every Monday at 9 AM
0 9 * * 1 cd /path/to/kinoweek && uv run python -m kinoweek.main
```

### GitHub Actions

Ready for GitHub Actions with scheduled workflows.

## Current Status

- **Astor Movies**: Fully working (57 OV showtimes, ~27 this week)
- **ZAG Arena**: Fully working (9 concerts)
- **Swiss Life Hall**: Fully working (10 concerts)
- **Capitol Hannover**: Fully working (10 concerts)

All 26 tests passing. End-to-end workflow verified.

## Roadmap

1. Lean MVP with stateless architecture
2. Configure all concert venue scrapers
3. Schedule weekly cron job
4. Consider movie deduplication (group showtimes per film)
5. Add ticket links to concert output

## Philosophy

> "A side project that ships is worth more than a perfect system that never launches."

This script prioritizes:
- **Shipping over perfection** - Works reliably, iterates based on usage
- **Simplicity over features** - No database, no state, just run it
- **Signal over noise** - Two curated sources, OV filtering
- **Reliability over cleverness** - Graceful failures, clear logs

See `docs/architecture.md` for detailed design decisions.
