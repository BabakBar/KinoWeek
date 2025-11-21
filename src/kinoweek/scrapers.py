"""
Scrapers for all three KinoWeek sources.

This module provides stateless scrapers for:
1. Astor Grand Cinema (OV movies)
2. Staatstheater Hannover (Opera/Ballet via iCal)
3. Concert venues (Big events)
"""

import logging
from typing import List
from datetime import datetime, timedelta
import httpx
from ics import Calendar
from bs4 import BeautifulSoup

from kinoweek.models import Event
from kinoweek.config import (
    ASTOR_API_URL,
    STAATSTHEATER_CALENDAR_URL,
    CONCERT_SOURCES,
    IGNORE_KEYWORDS,
    REQUEST_TIMEOUT,
    USER_AGENT,
)

logger = logging.getLogger(__name__)


def should_filter_event(title: str) -> bool:
    """
    Check if event should be filtered out based on keywords.

    Args:
        title: Event title to check

    Returns:
        True if event should be filtered out, False otherwise
    """
    title_lower = title.lower()
    return any(keyword.lower() in title_lower for keyword in IGNORE_KEYWORDS)


def is_original_version(language: str) -> bool:
    """
    Determine if a showtime is in original version (OV).

    OV movies are those NOT dubbed in German. This includes:
    - Movies in English, Japanese, Italian, Spanish, Russian, etc.
    - Movies with German subtitles (indicated by "Untertitel:")

    NOT OV:
    - Movies with "Sprache: Deutsch" without subtitles (German dubs)

    Args:
        language: Language string from the API (e.g., "Sprache: Englisch")

    Returns:
        True if this is an original version showing, False otherwise
    """
    if not language:
        return False

    # If it's German language, only include if it has subtitles
    if "Deutsch" in language:
        return "Untertitel:" in language

    # All other languages (English, Japanese, Italian, etc.) are original versions
    return True


def scrape_astor_movies() -> List[Event]:
    """
    Scrape movie schedules from Astor Grand Cinema Hannover's API.

    Returns OV (original version) movies only, converted to Event objects.

    Returns:
        List of Event objects with category="movie"
    """
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json; charset=utf-8",
        "Referer": "https://hannover.premiumkino.de/",
        "User-Agent": USER_AGENT,
    }

    events = []

    try:
        logger.info(f"Fetching Astor movies from {ASTOR_API_URL}")
        with httpx.Client() as client:
            response = client.get(ASTOR_API_URL, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

        # Build genre mapping
        genres_map = {genre['id']: genre['name'] for genre in data.get('genres', [])}

        # Build movie metadata
        movies = {movie['id']: movie for movie in data.get('movies', [])}
        performances = data.get('performances', [])

        for perf in performances:
            movie_id = perf.get('movieId')
            if movie_id not in movies:
                continue

            movie = movies[movie_id]
            title = movie.get('name')

            begin_str = perf.get('begin')
            if not begin_str:
                continue

            begin_dt = datetime.fromisoformat(begin_str)
            version = perf.get('language', 'Unknown Version')

            # Filter for Original Version (OV) movies only
            if not is_original_version(version):
                logger.debug(f"Skipping non-OV: {title} ({version})")
                continue

            # Build metadata
            metadata = {
                'duration': movie.get('minutes', 0),
                'rating': movie.get('rating', 0),
                'year': movie.get('year', 0),
                'country': movie.get('country', ''),
                'genres': [genres_map.get(gid, '') for gid in movie.get('genreIds', [])],
                'language': version,
            }

            # Create Event
            event = Event(
                title=title,
                date=begin_dt,
                venue="Astor Grand Cinema",
                url="https://hannover.premiumkino.de/",
                category="movie",
                metadata=metadata,
            )
            events.append(event)

        logger.info(f"Found {len(events)} OV movie showtimes from Astor")

    except httpx.RequestError as e:
        logger.error(f"Astor API request failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Astor scraping failed: {e}")
        raise

    return events


def scrape_staatstheater_events(start_date: datetime, end_date: datetime) -> List[Event]:
    """
    Scrape opera/ballet events from Staatstheater Hannover via HTML calendar.

    The calendar page uses client-side rendering, but we can still extract
    visible event data from the initial HTML load.

    Args:
        start_date: Start of date range to fetch
        end_date: End of date range to fetch

    Returns:
        List of Event objects with category="culture"
    """
    events = []

    try:
        logger.info(f"Fetching Staatstheater events from {STAATSTHEATER_CALENDAR_URL}")
        headers = {"User-Agent": USER_AGENT}

        with httpx.Client() as client:
            response = client.get(STAATSTHEATER_CALENDAR_URL, timeout=REQUEST_TIMEOUT, follow_redirects=True, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

        # Find event elements
        # The page uses article.event or similar structure
        event_items = soup.select('article.event, .event-item, article')

        if not event_items:
            logger.warning("No event items found on Staatstheater page")
            return events

        for item in event_items:
            try:
                # Extract title
                title_elem = item.select_one('h2, h3, h4, .title, .event-title')
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                # Filter by keywords
                if should_filter_event(title):
                    logger.debug(f"Filtering out: {title}")
                    continue

                # Extract date - try multiple selectors
                date_elem = item.select_one('time, .date, .event-date, .datetime')
                if not date_elem:
                    continue

                date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)

                # Parse date (try multiple formats)
                event_date = None
                for fmt in [
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d",
                    "%d.%m.%Y",
                    "%d.%m.%Y %H:%M",
                ]:
                    try:
                        event_date = datetime.strptime(date_str.strip(), fmt)
                        break
                    except ValueError:
                        continue

                if not event_date:
                    # Try parsing German date formats like "Fr, 22.11.2025 19:30"
                    import re
                    date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})\s*(\d{2}):(\d{2})', date_str)
                    if date_match:
                        day, month, year, hour, minute = date_match.groups()
                        event_date = datetime(int(year), int(month), int(day), int(hour), int(minute))
                    else:
                        logger.debug(f"Could not parse date: {date_str}")
                        continue

                # Filter by date range
                if not (start_date <= event_date <= end_date):
                    continue

                # Extract venue
                venue_elem = item.select_one('.venue, .location, .event-venue')
                venue = venue_elem.get_text(strip=True) if venue_elem else "Staatstheater Hannover"

                # Extract URL
                link_elem = item.select_one('a')
                event_url = link_elem.get('href') if link_elem else STAATSTHEATER_CALENDAR_URL
                if event_url.startswith('/'):
                    event_url = f"https://staatstheater-hannover.de{event_url}"

                event = Event(
                    title=title,
                    date=event_date,
                    venue=venue,
                    url=event_url,
                    category="culture",
                    metadata={},
                )
                events.append(event)

            except Exception as e:
                logger.debug(f"Error parsing Staatstheater event item: {e}")
                continue

        logger.info(f"Found {len(events)} culture events from Staatstheater")

    except httpx.RequestError as e:
        logger.error(f"Staatstheater request failed: {e}")
        logger.warning("Continuing without Staatstheater events")
    except Exception as e:
        logger.error(f"Staatstheater scraping failed: {e}")
        logger.warning("Continuing without Staatstheater events")

    return events


def scrape_hannover_concerts(limit: int = 10) -> List[Event]:
    """
    Scrape big concert/event listings from configured concert venues.

    This scraper fetches the "next big things" - major concerts and events
    that are worth knowing about months in advance.

    Args:
        limit: Maximum number of upcoming events to return (default: 5)

    Returns:
        List of Event objects with category="radar"
    """
    events = []

    # Check if any sources are enabled
    enabled_sources = [s for s in CONCERT_SOURCES if s.get('enabled', False)]
    if not enabled_sources:
        logger.info("No concert sources enabled (configure in config.py)")
        return events

    for source in enabled_sources:
        try:
            logger.info(f"Fetching concerts from {source['name']}: {source['url']}")
            headers = {"User-Agent": USER_AGENT}

            with httpx.Client() as client:
                response = client.get(source['url'], timeout=REQUEST_TIMEOUT, follow_redirects=True, headers=headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

            # Use venue-specific selectors
            selectors = source.get('selectors', {})
            source_name = source['name']

            if source_name == "ZAG Arena":
                event_items = soup.select(selectors.get('event', '.wpem-event-layout-wrapper'))

                for item in event_items[:limit]:
                    try:
                        # Title is in h3.wpem-heading-text
                        title_elem = item.select_one('.wpem-heading-text')
                        if not title_elem:
                            continue
                        title = title_elem.get_text(strip=True)

                        if should_filter_event(title):
                            continue

                        # Date is split into day and month divs
                        date_day_elem = item.select_one('.wpem-date')
                        date_month_elem = item.select_one('.wpem-month')
                        date_time_elem = item.select_one('.wpem-event-date-time-text')

                        if not (date_day_elem and date_month_elem):
                            continue

                        day_str = date_day_elem.get_text(strip=True)
                        month_str = date_month_elem.get_text(strip=True).rstrip('.')

                        # Get full date from date-time element (e.g., "20.11.2025")
                        if date_time_elem:
                            date_time_str = date_time_elem.get_text(strip=True)
                            import re
                            # Extract date in format "20.11.2025" and optionally time
                            date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', date_time_str)
                            if date_match:
                                day, month, year = date_match.groups()
                                # Try to find time too
                                time_match = re.search(r'(\d{1,2}):(\d{2})', date_time_str)
                                if time_match:
                                    hour, minute = time_match.groups()
                                    event_date = datetime(int(year), int(month), int(day), int(hour), int(minute))
                                else:
                                    event_date = datetime(int(year), int(month), int(day), 20, 0)
                            else:
                                # Fallback: use current year
                                month_map = {
                                    'jan': 1, 'feb': 2, 'mär': 3, 'mar': 3, 'apr': 4, 'mai': 5, 'may': 5,
                                    'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'oct': 10,
                                    'nov': 11, 'dez': 12, 'dec': 12
                                }
                                month = month_map.get(month_str.lower(), 1)
                                event_date = datetime(2025, month, int(day_str), 20, 0)
                        else:
                            # No date-time element, use day and month only
                            month_map = {
                                'jan': 1, 'feb': 2, 'mär': 3, 'mar': 3, 'apr': 4, 'mai': 5, 'may': 5,
                                'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'oct': 10,
                                'nov': 11, 'dez': 12, 'dec': 12
                            }
                            month = month_map.get(month_str.lower(), 1)
                            event_date = datetime(2025, month, int(day_str), 20, 0)

                        # Link is in the main anchor tag
                        link_elem = item.select_one('a.wpem-event-action-url')
                        if not link_elem:
                            continue
                        event_url = link_elem.get('href')
                        if not event_url.startswith('http'):
                            event_url = f"https://www.zag-arena-hannover.de{event_url}"

                        event = Event(
                            title=title,
                            date=event_date,
                            venue=source_name,
                            url=event_url,
                            category="radar",
                            metadata={},
                        )
                        events.append(event)

                    except Exception as e:
                        logger.debug(f"Error parsing {source_name} event: {e}")
                        continue

            elif source_name in ["Swiss Life Hall", "Capitol Hannover"]:
                # Both use the same "hc-kartenleger" card system
                event_items = soup.select(selectors.get('event', "a.hc-card-link-wrapper"))

                base_url = "https://www.swisslife-hall.de" if source_name == "Swiss Life Hall" else "https://www.capitol-hannover.de"

                for item in event_items[:limit]:
                    try:
                        # Title is in the 'title' attribute of the link
                        title = item.get('title')
                        if not title:
                            # Fallback to h4/h3 if title attribute not present
                            title_elem = item.select_one('h4, h3')
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                            else:
                                continue

                        if should_filter_event(title):
                            continue

                        # Date is in a <time> element with format like "AB22NOV2025"
                        date_elem = item.select_one('time')
                        if not date_elem:
                            continue

                        date_str = date_elem.get_text(strip=True)
                        # Parse "AB22NOV2025" format - extract day, month, year
                        import re
                        date_match = re.search(r'(\d{1,2})([A-ZÄÖÜa-zäöü]+)(\d{4})', date_str)
                        if not date_match:
                            continue

                        day, month_str, year = date_match.groups()
                        month_map = {
                            'jan': 1, 'januar': 1,
                            'feb': 2, 'februar': 2,
                            'mär': 3, 'märz': 3, 'mar': 3,
                            'apr': 4, 'april': 4,
                            'mai': 5, 'may': 5,
                            'jun': 6, 'juni': 6,
                            'jul': 7, 'juli': 7,
                            'aug': 8, 'august': 8,
                            'sep': 9, 'september': 9,
                            'okt': 10, 'oktober': 10, 'oct': 10,
                            'nov': 11, 'november': 11,
                            'dez': 12, 'dezember': 12, 'dec': 12,
                        }
                        month = month_map.get(month_str.lower(), 1)
                        event_date = datetime(int(year), month, int(day), 20, 0)  # Default to 8 PM

                        event_url = item.get('href')
                        if not event_url.startswith('http'):
                            event_url = f"{base_url}{event_url}"

                        event = Event(
                            title=title,
                            date=event_date,
                            venue=source_name,
                            url=event_url,
                            category="radar",
                            metadata={},
                        )
                        events.append(event)

                    except Exception as e:
                        logger.debug(f"Error parsing {source_name} event: {e}")
                        continue

            logger.info(f"Found {len([e for e in events if e.venue == source_name])} events from {source_name}")

        except httpx.RequestError as e:
            logger.error(f"{source['name']} request failed: {e}")
            logger.warning(f"Continuing without {source['name']} events")
        except Exception as e:
            logger.error(f"{source['name']} scraping failed: {e}")
            logger.warning(f"Continuing without {source['name']} events")

    return events


def get_all_events() -> dict:
    """
    Fetch all events from all sources and categorize them.

    Returns:
        Dictionary with keys:
        - 'movies_this_week': List of movie events in next 7 days
        - 'culture_this_week': List of culture events in next 7 days
        - 'big_events_radar': List of upcoming big events (beyond next 7 days)
    """
    today = datetime.now()
    next_week = today + timedelta(days=7)

    # Gather from all sources
    logger.info("Fetching events from all sources...")

    movies = scrape_astor_movies()
    culture = scrape_staatstheater_events(today, next_week)
    radar = scrape_hannover_concerts(limit=10)

    # Filter movies to this week only
    movies_this_week = [m for m in movies if m.is_this_week()]

    # Culture events are already filtered by date range
    culture_this_week = culture

    # Filter radar events to EXCLUDE this week (only show future events)
    radar_filtered = [r for r in radar if r.date > next_week]

    # Sort all lists by date
    movies_this_week.sort(key=lambda x: x.date)
    culture_this_week.sort(key=lambda x: x.date)
    radar_filtered.sort(key=lambda x: x.date)

    return {
        'movies_this_week': movies_this_week,
        'culture_this_week': culture_this_week,
        'big_events_radar': radar_filtered,
    }
