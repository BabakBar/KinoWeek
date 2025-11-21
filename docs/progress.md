# KinoWeek Development Progress

## Overview

KinoWeek - A weekly event aggregator for Hannover that fetches OV movies from Astor Grand Cinema and concerts from major venues, delivering a formatted digest via Telegram.

## Project Structure

```
KinoWeek/
├── src/kinoweek/           # Main package
│   ├── __init__.py        # Package exports with lazy imports
│   ├── models.py          # Event dataclass (unified structure)
│   ├── config.py          # URLs, venues, settings
│   ├── scrapers.py        # AstorMovieScraper + ConcertVenueScraper
│   ├── notifier.py        # Message formatting & Telegram integration
│   └── main.py            # Orchestration & CLI
├── tests/                 # Test suite (26 tests)
├── docs/                  # Documentation
├── output/                # Local test results
├── pyproject.toml         # Modern Python config with ruff/mypy
└── .env.example          # Environment variables template
```

## Development Phases

### Phase 1-5: Initial Development (Historical)
- MVP implementation with Playwright browser automation
- Discovered Playwright was blocked by anti-scraping measures
- Pivoted to direct API access (backend.premiumkino.de)
- OV filtering implementation
- Telegram integration

### Phase 6: Multi-Source Architecture
- **Status**: Completed
- **Date**: 2025-11-21
- **Achievements**:
  - Added Staatstheater Hannover scraper (culture events)
  - Added concert venue scrapers (ZAG Arena, Swiss Life Hall, Capitol)
  - Unified Event model for all sources
  - Three-section message format (Movies, Culture, Radar)

### Phase 7: Codebase Modernization
- **Status**: Completed
- **Date**: 2025-11-21
- **Achievements**:
  - **Removed Legacy Code**: Deleted deprecated `scraper.py` module
  - **Modern Python**: Using 3.13+ features (slots, kw_only, Literal types)
  - **Class-Based Scrapers**: Abstract `BaseScraper` with implementations
  - **Type Safety**: Comprehensive type hints, TypedDict for configs
  - **Enhanced Testing**: 26 tests with proper mocking
  - **Better Organization**: Clear section headers, docstrings throughout

### Phase 8: Streamlining
- **Status**: Completed
- **Date**: 2025-11-21
- **Achievements**:
  - **Removed Staatstheater**: Non-functional scraper removed (page structure changed)
  - **Enhanced Concert Formatting**: German day names (Sa, So, Mo, etc.)
  - **Expanded Date Display**: "Sa, 29. Nov | 20:00 @ ZAG Arena"
  - **Increased Event Limit**: 15 concerts per venue (up from 10)
  - **Two-Source Architecture**: Movies + Concerts (simpler, more reliable)

## Current Architecture

### Two Event Sources

1. **Astor Grand Cinema** (Movies)
   - Direct JSON API access
   - OV filtering (no German dubs)
   - Metadata: duration, rating, year, country, genres, language
   - Timeframe: This week (7 days)

2. **Concert Venues** (Concerts)
   - HTML scraping with BeautifulSoup
   - Venues: ZAG Arena, Swiss Life Hall, Capitol Hannover
   - Metadata: time, venue
   - Timeframe: Beyond 7 days (on the radar)

### Module Responsibilities

#### `models.py`
- `Event` dataclass with slots and kw_only
- `Literal["movie", "culture", "radar"]` for category
- Helper methods for date formatting

#### `config.py`
- `ASTOR_API_URL`: Movie API endpoint
- `CONCERT_VENUES`: Tuple of VenueConfig TypedDicts
- `GERMAN_MONTH_MAP`: Date parsing support
- HTTP client settings

#### `scrapers.py`
- `BaseScraper`: Abstract base class
- `AstorMovieScraper`: JSON API client
- `ConcertVenueScraper`: HTML scraper with venue-specific parsing
- `fetch_all_events()`: Orchestration function

#### `notifier.py`
- German day/month mappings for localized output
- Section formatters for movies and concerts
- Telegram API integration
- File backup (JSON + text)

#### `main.py`
- CLI with `--local` flag
- Environment validation
- Logging configuration
- Workflow orchestration

## Current Status (2025-11-21)

### Working Features
- Astor Movies: 57 OV showtimes, ~27 this week
- ZAG Arena: 9 concerts
- Swiss Life Hall: 10 concerts
- Capitol Hannover: 10 concerts
- All 26 tests passing
- End-to-end workflow verified

### Output Format

**Movies (This Week)**:
```
*Fri 21.11.*
  *Chainsaw Man - The Movie: Reze Arc (2025)*
  _1h41m | FSK16_
  22:50 (JP, UT:DE)
```

**On The Radar (Concerts)**:
```
*LUCIANO*
Sa, 29. Nov | 20:00 @ ZAG Arena
```

### Technical Metrics
- **Test Coverage**: 26 passing tests
- **Execution Time**: ~6 seconds
- **API Calls**: 4 total (1 Astor + 3 venues)
- **Python Version**: 3.13+
- **Dependencies**: httpx, beautifulsoup4, python-dotenv

## Future Improvements

### Potential Enhancements
1. **Movie Deduplication**: Group showtimes per film
2. **Ticket Links**: Include URLs in concert output
3. **Genre Display**: Show movie genres in output
4. **Additional Venues**: Easy to add via config

### Extension Points
- New scrapers: Extend `BaseScraper` class
- New channels: Add alongside Telegram
- Persistence: Add database for historical analysis

## Lessons Learned

### Technical Insights
- **API > Browser Automation**: Direct API access is faster and more reliable
- **Graceful Degradation**: Handle scraper failures without crashing
- **Type Safety**: Modern Python features catch bugs early
- **Class-Based Architecture**: Easier to extend and test

### Development Process
- **Remove Dead Code**: Staatstheater removal simplified codebase
- **Test Everything**: 26 tests gave confidence to refactor
- **Iterate on Formatting**: Multiple passes to polish output
- **Document as You Go**: Keep docs in sync with code

## Commands

```bash
# Run locally (saves to output/)
uv run python -m kinoweek.main --local

# Run with Telegram
uv run python -m kinoweek.main

# Run tests
uv run python -m pytest tests/ -v

# Check output
cat output/latest_message.txt
cat output/events.json
```
