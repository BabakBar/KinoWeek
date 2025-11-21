# Architecture Document: KinoWeek

## Executive Summary

KinoWeek is a stateless, weekly event aggregator for Hannover that fetches OV movies and concerts from two sources and delivers a formatted digest via Telegram. The system uses modern Python (3.13+) with class-based scrapers, type hints, and comprehensive testing.

## System Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Scheduler     │───▶│   Scrapers       │───▶│   Notifier      │
│  (Cron/Manual)  │    │  (httpx/BS4)     │    │  (Telegram)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Weekly Job    │    │  • Astor API     │    │   Bot API       │
│   (Stateless)   │    │  • Venue HTML    │    │   + File Backup │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Component Architecture

### 1. Data Model (`models.py`)

**Purpose**: Unified event structure for all sources

```python
@dataclass(slots=True, kw_only=True)
class Event:
    title: str
    date: datetime
    venue: str
    url: str
    category: Literal["movie", "culture", "radar"]
    metadata: dict[str, str | int | list[str]] = field(default_factory=dict)
```

**Features**:
- `slots=True` for memory efficiency
- `kw_only=True` for explicit construction
- `Literal` type for category validation
- Helper methods: `format_date_short()`, `format_time()`, `is_this_week()`

### 2. Configuration (`config.py`)

**Purpose**: Centralized settings with type safety

**Key Components**:
- `ASTOR_API_URL`: Movie API endpoint
- `CONCERT_VENUES`: Tuple of `VenueConfig` TypedDicts with selectors
- `GERMAN_MONTH_MAP`: Date parsing support
- `Final` constants for immutability

### 3. Scrapers (`scrapers.py`)

**Architecture**: Class-based with abstract base

```python
class BaseScraper(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @abstractmethod
    def fetch(self) -> list[Event]: ...
```

**Implementations**:

#### AstorMovieScraper
- **Source**: `backend.premiumkino.de` JSON API
- **Filter**: Original Version only (no German dubs)
- **Output**: Events with `category="movie"`
- **Metadata**: duration, rating, year, country, genres, language

```python
# OV Detection Logic
def _is_original_version(language: str) -> bool:
    if "Deutsch" in language:
        return "Untertitel:" in language  # German subs = OV
    return True  # All other languages are OV
```

#### ConcertVenueScraper
- **Sources**: ZAG Arena, Swiss Life Hall, Capitol Hannover
- **Method**: HTML scraping with BeautifulSoup
- **Output**: Events with `category="radar"`
- **Metadata**: time, location/subtitle

**Venue-Specific Parsing**:
- ZAG Arena: `.wpem-event-layout-wrapper` containers
- Swiss Life Hall / Capitol: `.hc-card-link-wrapper` cards

### 4. Notifier (`notifier.py`)

**Purpose**: Message formatting and delivery

**Key Functions**:
- `format_message()`: Creates Telegram-ready message
- `send_telegram_message()`: Posts to Telegram Bot API
- `save_to_file()`: JSON and text backup
- `notify()`: Orchestrates local/remote delivery

**Message Sections**:
1. **Movies (This Week)**: Grouped by date, with metadata
2. **On The Radar**: Concerts with German day names

**Date Formatting**:
```python
# German day/month names for concert display
_GERMAN_DAYS = {0: "Mo", 1: "Di", 2: "Mi", 3: "Do", 4: "Fr", 5: "Sa", 6: "So"}
_GERMAN_MONTHS = {1: "Jan", 2: "Feb", ..., 12: "Dez"}

# Output: "Sa, 29. Nov | 20:00 @ ZAG Arena"
```

### 5. Main Orchestration (`main.py`)

**Entry Point**: `main()` → `run(local_only=False)`

**Workflow**:
1. Configure logging (console + file)
2. Validate environment (Telegram credentials)
3. Call `fetch_all_events()`
4. Call `notify(events_data, local_only=...)`
5. Exit with appropriate status code

## Data Flow

### Event Aggregation

```
AstorMovieScraper.fetch()     ─┐
                               ├─► fetch_all_events()
ConcertVenueScraper.fetch()   ─┘
         │
         ▼
┌────────────────────────────────────┐
│ Categorization:                    │
│ • movies_this_week (next 7 days)   │
│ • big_events_radar (beyond 7 days) │
└────────────────────────────────────┘
         │
         ▼
    dict[str, list[Event]]
```

### Output Data Structure

```python
{
    "movies_this_week": [Event(...), ...],
    "big_events_radar": [Event(...), ...],
}
```

### JSON Export Format

```json
{
  "movies_this_week": [
    {
      "title": "Wicked: Teil 2",
      "date": "2025-11-22T13:45:00",
      "venue": "Astor Grand Cinema",
      "url": "https://hannover.premiumkino.de/",
      "category": "movie",
      "metadata": {
        "duration": 137,
        "rating": 12,
        "year": 2025,
        "language": "Sprache: Englisch"
      }
    }
  ],
  "big_events_radar": [
    {
      "title": "LUCIANO",
      "date": "2025-11-29T20:00:00",
      "venue": "ZAG Arena",
      "url": "https://www.zag-arena-hannover.de/...",
      "category": "radar",
      "metadata": {"time": "20:00"}
    }
  ]
}
```

## Error Handling

### Graceful Degradation
- Individual scraper failures don't crash the workflow
- Empty results are handled gracefully
- Network errors logged with context

### Retry Strategy (Future Enhancement)
- Exponential backoff for transient failures
- Maximum retry attempts configurable

## Testing Strategy

### Test Coverage (26 tests)

1. **Event Model Tests** (6 tests)
   - Creation, metadata, date formatting, week detection

2. **Scraper Tests** (7 tests)
   - Source names, API parsing, OV filtering, empty responses

3. **Notifier Tests** (10 tests)
   - Message formatting, sections, Telegram API, local mode

4. **Integration Tests** (3 tests)
   - Full workflow with mocked scrapers

### Running Tests

```bash
uv run python -m pytest tests/ -v
```

## Performance

### Current Metrics
- **Execution Time**: ~6 seconds (network dependent)
- **Memory Usage**: < 100MB
- **API Calls**: 4 total (1 Astor + 3 venues)

### Optimizations
- Single API call for all Astor data
- Connection reuse via httpx.Client context manager
- In-memory processing (no database)

## Security

### Secrets Management
- Environment variables for Telegram credentials
- `.env` file support via python-dotenv
- No hardcoded secrets

### Network Security
- HTTPS only
- Standard User-Agent header
- Timeout configuration (30s)

## Deployment Options

### 1. Local Cron Job
```bash
0 9 * * 1 cd /path/to/kinoweek && uv run python -m kinoweek.main
```

### 2. GitHub Actions
```yaml
on:
  schedule:
    - cron: '0 9 * * 1'  # Monday 9 AM UTC
```

### 3. Container (Docker/Coolify)
- Scheduled task execution
- Environment variable injection

## Future Enhancements

### Potential Improvements
1. **Movie Deduplication**: Group showtimes per film
2. **Ticket Links**: Include URLs in concert output
3. **Genre Display**: Show movie genres
4. **Additional Venues**: Easy to add via config

### Extension Points
- New scrapers: Extend `BaseScraper`
- New notification channels: Add alongside Telegram
- Database persistence: Add for historical analysis

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.13+ | Modern features, type hints |
| HTTP Client | httpx | Async-ready, clean API |
| HTML Parsing | BeautifulSoup4 | Robust HTML extraction |
| Package Manager | uv | Fast, modern tooling |
| Testing | pytest | Comprehensive test suite |
| Linting | ruff | Fast, comprehensive |
| Type Checking | mypy (strict) | Type safety |

## File Structure

```
KinoWeek/
├── src/kinoweek/
│   ├── __init__.py      # Package with lazy imports
│   ├── models.py        # Event dataclass
│   ├── config.py        # URLs, venues, settings
│   ├── scrapers.py      # AstorMovieScraper, ConcertVenueScraper
│   ├── notifier.py      # Format + Telegram + file output
│   └── main.py          # CLI and orchestration
├── tests/
│   └── test_scraper.py  # 26 tests
├── docs/
│   └── architecture.md  # This document
├── output/              # Generated files
├── pyproject.toml       # Modern Python config
└── README.md            # Quick start guide
```

## Conclusion

KinoWeek demonstrates a clean, maintainable architecture for a weekly aggregation system:
- **Modular design** with clear separation of concerns
- **Type safety** with modern Python features
- **Comprehensive testing** for reliability
- **Graceful degradation** for robustness
- **Simple deployment** with multiple options

The stateless design keeps complexity low while delivering a useful weekly digest.
