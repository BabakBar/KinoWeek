"""Export functions for different output formats.

Provides specialized export functions for:
- JSON (enhanced with metadata)
- Markdown (human-readable digest)
- Weekly archives for historical tracking

CSV exports are in the csv_exporters module.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

# Re-export CSV functions for backward compatibility
from kinoweek.csv_exporters import (
    export_concerts_csv,
    export_movies_csv,
    export_movies_grouped_csv,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from kinoweek.models import Event
    from kinoweek.output import GroupedMovie

__all__ = [
    # CSV exports (re-exported)
    "export_movies_csv",
    "export_movies_grouped_csv",
    "export_concerts_csv",
    # JSON/Markdown/Archive exports
    "export_enhanced_json",
    "export_markdown_digest",
    "archive_weekly_data",
]

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================


def _format_duration(minutes: int) -> str:
    """Format duration in minutes to human-readable string."""
    if minutes <= 0:
        return ""
    hours, mins = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h{mins}m" if mins else f"{hours}h"
    return f"{mins}m"


# =============================================================================
# JSON Export (Enhanced)
# =============================================================================


def export_enhanced_json(
    movies: Sequence[Event],
    concerts: Sequence[Event],
    grouped_movies: list[GroupedMovie],
    output_path: Path,
    week_num: int,
    year: int,
) -> None:
    """Export enhanced JSON with all data.

    Args:
        movies: List of movie events.
        concerts: List of concert events.
        grouped_movies: List of grouped movies.
        output_path: Path to output directory.
        week_num: Current week number.
        year: Current year.
    """
    json_path = output_path / "events.json"

    data = {
        "meta": {
            "week": week_num,
            "year": year,
            "generated_at": datetime.now().isoformat(),
            "sources": ["Astor Grand Cinema", "ZAG Arena", "Swiss Life Hall", "Capitol Hannover"],
            "total_movie_showtimes": len(movies),
            "total_unique_films": len(grouped_movies),
            "total_concerts": len(concerts),
        },
        "movies": {
            "unique_films": [
                {
                    "title": m.title,
                    "year": m.year,
                    "duration_min": m.duration_min,
                    "rating": f"FSK{m.rating}" if m.rating else "",
                    "country": m.country,
                    "genres": m.genres,
                    "synopsis": m.synopsis,
                    "poster_url": m.poster_url,
                    "trailer_url": m.trailer_url,
                    "cast": m.cast[:5],  # Limit to top 5
                    "ticket_url": m.ticket_url,
                    "venue": m.venue,
                    "showtimes": [
                        {
                            "date": st.date,
                            "time": st.time,
                            "language": st.language,
                        }
                        for st in m.showtimes
                    ],
                }
                for m in grouped_movies
            ],
            "all_showtimes": [
                {
                    "title": e.title,
                    "date": e.date.isoformat(),
                    "venue": e.venue,
                    "url": e.url,
                    "metadata": dict(e.metadata),
                }
                for e in movies
            ],
        },
        "concerts": [
            {
                "artist": e.title,
                "date": e.date.isoformat(),
                "venue": e.venue,
                "url": e.url,
                "time": e.metadata.get("time", "20:00"),
                "event_type": e.metadata.get("event_type", "concert"),
                "status": e.metadata.get("status", "available"),
                "image_url": e.metadata.get("image_url", ""),
                "address": e.metadata.get("address", ""),
            }
            for e in concerts
        ],
    }

    json_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("Exported enhanced JSON to %s", json_path)


# =============================================================================
# Markdown Digest
# =============================================================================


def export_markdown_digest(
    grouped_movies: list[GroupedMovie],
    concerts: Sequence[Event],
    output_path: Path,
    week_num: int,
    year: int,
) -> None:
    """Export a nice markdown digest.

    Args:
        grouped_movies: List of grouped movies.
        concerts: List of concert events.
        output_path: Path to output directory.
        week_num: Current week number.
        year: Current year.
    """
    md_path = output_path / "weekly_digest.md"

    lines = [
        f"# Hannover Week {week_num} ({year})",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "---",
        "",
        "## Movies (Original Version)",
        "",
        f"**{len(grouped_movies)} films** with **{sum(len(m.showtimes) for m in grouped_movies)} showtimes** this week",
        "",
    ]

    # Movies section
    for movie in grouped_movies:
        rating_str = f"FSK{movie.rating}" if movie.rating else ""
        duration_str = _format_duration(movie.duration_min)
        genres_str = ", ".join(movie.genres) if movie.genres else ""

        lines.append(f"### {movie.title} ({movie.year})")
        lines.append("")

        meta_parts = []
        if duration_str:
            meta_parts.append(duration_str)
        if rating_str:
            meta_parts.append(rating_str)
        if movie.country:
            meta_parts.append(movie.country)
        if genres_str:
            meta_parts.append(genres_str)

        if meta_parts:
            lines.append(f"*{' | '.join(meta_parts)}*")
            lines.append("")

        if movie.synopsis:
            synopsis = movie.synopsis[:300] + "..." if len(movie.synopsis) > 300 else movie.synopsis
            lines.append(f"> {synopsis}")
            lines.append("")

        # Showtimes table
        lines.append("| Date | Time | Language |")
        lines.append("|------|------|----------|")
        for st in movie.showtimes:
            lines.append(f"| {st.date} | {st.time} | {st.language} |")
        lines.append("")

        if movie.poster_url:
            lines.append(f"[Poster]({movie.poster_url}) | [Tickets]({movie.ticket_url})")
        else:
            lines.append(f"[Tickets]({movie.ticket_url})")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Concerts section
    lines.extend([
        "## On The Radar",
        "",
        f"**{len(concerts)} upcoming events**",
        "",
        "| Date | Artist | Venue | Status |",
        "|------|--------|-------|--------|",
    ])

    for event in concerts:
        date_str = event.date.strftime("%Y-%m-%d")
        time_str = event.metadata.get("time", "20:00")
        status = event.metadata.get("status", "available")
        status_display = "Available" if status == "available" else "Sold Out"

        lines.append(
            f"| {date_str} {time_str} | [{event.title}]({event.url}) | {event.venue} | {status_display} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Data sourced from Astor Grand Cinema, ZAG Arena, Swiss Life Hall, Capitol Hannover*")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    logger.info("Exported markdown digest to %s", md_path)


# =============================================================================
# Weekly Archive
# =============================================================================


def archive_weekly_data(
    movies: Sequence[Event],
    concerts: Sequence[Event],
    output_path: Path,
    week_num: int,
    year: int,
) -> None:
    """Archive the weekly data snapshot.

    Args:
        movies: List of movie events.
        concerts: List of concert events.
        output_path: Path to output directory.
        week_num: Current week number.
        year: Current year.
    """
    archive_dir = output_path / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_path = archive_dir / f"{year}-W{week_num:02d}.json"

    data = {
        "meta": {
            "week": week_num,
            "year": year,
            "archived_at": datetime.now().isoformat(),
        },
        "movies": [
            {
                "title": e.title,
                "date": e.date.isoformat(),
                "venue": e.venue,
                "url": e.url,
                "metadata": dict(e.metadata),
            }
            for e in movies
        ],
        "concerts": [
            {
                "title": e.title,
                "date": e.date.isoformat(),
                "venue": e.venue,
                "url": e.url,
                "metadata": dict(e.metadata),
            }
            for e in concerts
        ],
    }

    archive_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("Archived weekly data to %s", archive_path)
