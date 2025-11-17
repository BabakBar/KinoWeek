"""Scraper module for Astor Kino website using direct API calls."""

import logging
from typing import Dict, List, Any
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class MovieInfo:
    """Data class for movie information."""
    def __init__(self, title: str, duration: int = 0, rating: int = 0,
                 year: int = 0, country: str = "", genres: List[str] = None):
        self.title = title
        self.duration = duration
        self.rating = rating
        self.year = year
        self.country = country
        self.genres = genres or []


class Showtime:
    """Data class for a movie showtime."""
    def __init__(self, datetime_obj: datetime, time_str: str, version: str):
        self.datetime = datetime_obj
        self.time_str = time_str
        self.version = version


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

    # If it's German language, only include if it has subtitles (meaning it's OV with German subs)
    if "Deutsch" in language:
        # Include if it has subtitles (e.g., "Sprache: Englisch, Untertitel: Deutsch")
        # or German subtitles on original language (e.g., "Sprache: Japanisch, Untertitel: Deutsch")
        return "Untertitel:" in language

    # All other languages (English, Japanese, Italian, etc.) are original versions
    return True


def scrape_movies() -> Dict[str, Any]:
    """
    Scrape movie schedules from Astor Grand Cinema Hannover's API.

    Returns:
        Dictionary with schedule data sorted by date, including movie metadata
    """
    api_url = "https://backend.premiumkino.de/v1/de/hannover/program"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json; charset=utf-8",
        "Referer": "https://hannover.premiumkino.de/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    }

    # Structure: {date_str: {movie_title: {'info': MovieInfo, 'showtimes': [Showtime]}}}
    schedule_data: Dict[str, Dict[str, Dict[str, Any]]] = {}

    try:
        logger.info(f"Fetching data from {api_url}")
        with httpx.Client() as client:
            response = client.get(api_url, headers=headers)
            response.raise_for_status()
            data = response.json()

        # Build genre mapping
        genres_map = {genre['id']: genre['name'] for genre in data.get('genres', [])}

        # Build movie metadata
        movies = {movie['id']: movie for movie in data.get('movies', [])}
        performances = data.get('performances', [])

        # Temporary structure to hold data with datetime objects for sorting
        temp_schedule: Dict[datetime, Dict[str, Dict[str, Any]]] = {}

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
            date_only = begin_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            time_str = begin_dt.strftime("%H:%M")

            version = perf.get('language', 'Unknown Version')

            # Filter for Original Version (OV) movies only
            if not is_original_version(version):
                logger.debug(f"Skipping non-OV showtime: {title} at {time_str} ({version})")
                continue

            # Extract movie metadata
            movie_info = MovieInfo(
                title=title,
                duration=movie.get('minutes', 0),
                rating=movie.get('rating', 0),
                year=movie.get('year', 0),
                country=movie.get('country', ''),
                genres=[genres_map.get(gid, '') for gid in movie.get('genreIds', [])]
            )

            # Initialize date entry if needed
            if date_only not in temp_schedule:
                temp_schedule[date_only] = {}

            # Initialize movie entry if needed
            if title not in temp_schedule[date_only]:
                temp_schedule[date_only][title] = {
                    'info': movie_info,
                    'showtimes': []
                }

            # Add showtime
            showtime = Showtime(begin_dt, time_str, version)
            temp_schedule[date_only][title]['showtimes'].append(showtime)

        # Sort dates chronologically and convert to formatted strings
        sorted_dates = sorted(temp_schedule.keys())
        for date_obj in sorted_dates:
            date_str = date_obj.strftime("%a %d.%m.")
            schedule_data[date_str] = temp_schedule[date_obj]

        logger.info(f"Filtered to {sum(len(movies) for movies in schedule_data.values())} OV movies across {len(schedule_data)} dates")

    except httpx.RequestError as e:
        logger.error(f"HTTP request failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise

    return schedule_data