"""
Configuration settings for KinoWeek scrapers.

All URLs and settings are centralized here for easy updates.
"""

# Astor Grand Cinema API
ASTOR_API_URL = "https://backend.premiumkino.de/v1/de/hannover/program"

# Staatstheater Hannover
# Using HTML scraping since iCal feed is not available
STAATSTHEATER_CALENDAR_URL = "https://staatstheater-hannover.de/de_DE/kalender"

# Concert venues to scrape (verified URLs)
CONCERT_SOURCES = [
    {
        "name": "ZAG Arena",
        "url": "https://www.zag-arena-hannover.de/veranstaltungen/",
        "enabled": True,
        "selectors": {
            "container": ".wpem-event-listings",
            "event": ".wpem-event-layout-wrapper",
            "title": ".wpem-heading-text a",
            "date": ".wpem-from-date",
            "location": ".wpem-event-infomation",
        }
    },
    {
        "name": "Swiss Life Hall",
        "url": "https://www.swisslife-hall.de/events/",
        "enabled": True,
        "selectors": {
            "event": "a.hc-card-link-wrapper",
            "title": "h4, h3",
            "date": ".hc-date-info",
            "venue": "Swiss Life Hall",
        }
    },
    {
        "name": "Capitol Hannover",
        "url": "https://www.capitol-hannover.de/events/",
        "enabled": True,
        "selectors": {
            "event": "a.hc-card-link-wrapper",
            "title": "h4, h3",
            "date": ".hc-date-info",
            "venue": "Capitol Hannover",
        }
    },
]

# Keywords to filter out (noise reduction)
IGNORE_KEYWORDS = [
    "Führung",
    "Einführung",
    "Kindertheater",
    "Kindertanz",
    "Workshop",
    "Probe",
    "Geschlossene Veranstaltung",
]

# HTTP request settings
REQUEST_TIMEOUT = 30.0  # seconds
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
