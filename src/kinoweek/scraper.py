"""Scraper module for Astor Kino website automation and data extraction."""

import logging
from typing import Dict, List, Optional
from playwright.sync_api import sync_playwright, Browser, Page

logger = logging.getLogger(__name__)


def scrape_movies() -> Dict[str, Dict[str, List[str]]]:
    """
    Scrape movie schedules from Astor Grand Cinema Hannover website.

    Returns:
        Dictionary with dates as keys and movies/showtimes as values.
        Example: {"Mon 24.11": {"Wicked": ["19:30 (Cinema 10, 2D OV)"]}}
    """
    url = "https://hannover.premiumkino.de/programm/originalfassung"
    schedule_data: Dict[str, Dict[str, List[str]]] = {}

    with sync_playwright() as p:
        try:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to website
            logger.info(f"Navigating to {url}")
            page.goto(url, wait_until="domcontentloaded")
            
            # Handle cookie consent if present
            _handle_cookie_consent(page)
            
            # Find date tabs
            date_tabs = page.query_selector_all(".nav-link[href*='#']")
            if not date_tabs:
                logger.warning("No date tabs found, trying alternative selectors")
                date_tabs = page.query_selector_all("[data-date], .date-tab, .tab-link")
            
            logger.info(f"Found {len(date_tabs)} date tabs")
            
            # Process each date tab
            for i, tab in enumerate(date_tabs):
                try:
                    # Extract date text
                    date_text = tab.text_content()
                    if not date_text or not date_text.strip():
                        continue
                    date_text = date_text.strip()
                    
                    logger.info(f"Processing date: {date_text}")
                    
                    # Click tab
                    tab.click()
                    page.wait_for_timeout(1000)  # Wait for content to load
                    
                    # Extract movies for this date
                    movies_data = _extract_movies_from_page(page)
                    if movies_data:
                        schedule_data[date_text] = movies_data
                    
                except Exception as e:
                    logger.error(f"Error processing tab {i}: {e}")
                    continue
            
            browser.close()
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            raise
    
    return schedule_data


def _handle_cookie_consent(page: Page) -> None:
    """Handle cookie consent banner if present."""
    try:
        # Common cookie consent selectors
        cookie_selectors = [
            "button[data-cy='accept-cookies']",
            "button[id*='accept']",
            "button[class*='accept']",
            ".cookie-accept",
            "#cookie-consent button",
            ".consent-button"
        ]
        
        for selector in cookie_selectors:
            button = page.query_selector(selector)
            if button:
                button.click()
                logger.info("Clicked cookie consent button")
                page.wait_for_timeout(500)
                break
    except Exception as e:
        logger.debug(f"No cookie consent handling needed: {e}")


def _extract_movies_from_page(page: Page) -> Dict[str, List[str]]:
    """Extract movie data from the current page."""
    movies_data: Dict[str, List[str]] = {}
    
    try:
        # Look for movie containers - try multiple selectors
        movie_selectors = [
            ".movie-item",
            ".film-item", 
            ".performance-item",
            ".show-item",
            "[data-movie]",
            ".movie-list-item"
        ]
        
        movie_elements = []
        for selector in movie_selectors:
            movie_elements = page.query_selector_all(selector)
            if movie_elements:
                break
        
        if not movie_elements:
            logger.warning("No movie elements found, trying broader approach")
            # Try to find any element that might contain movie info
            movie_elements = page.query_selector_all("div[class*='movie'], div[class*='film'], div[class*='show']")
        
        logger.info(f"Found {len(movie_elements)} movie elements")
        
        for movie_element in movie_elements:
            try:
                # Extract movie title
                title_element = movie_element.query_selector("h1, h2, h3, .title, .movie-title")
                if not title_element:
                    continue
                
                title = title_element.text_content()
                if not title or not title.strip():
                    continue
                title = title.strip()
                
                # Extract showtimes
                showtimes = _extract_showtimes(movie_element)
                
                if showtimes:
                    if title not in movies_data:
                        movies_data[title] = []
                    movies_data[title].extend(showtimes)
                
            except Exception as e:
                logger.debug(f"Error extracting movie data: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Error extracting movies from page: {e}")
    
    return movies_data


def _extract_showtimes(movie_element) -> List[str]:
    """Extract showtime information from a movie element."""
    showtimes: List[str] = []
    
    try:
        # Look for showtime elements
        showtime_selectors = [
            ".showtime",
            ".time",
            ".performance-time",
            "[data-time]",
            ".show-time"
        ]
        
        showtime_elements = []
        for selector in showtime_selectors:
            showtime_elements = movie_element.query_selector_all(selector)
            if showtime_elements:
                break
        
        for showtime_element in showtime_elements:
            try:
                # Get time text
                time_text = showtime_element.text_content()
                if not time_text or not time_text.strip():
                    continue
                time_text = time_text.strip()
                
                # Look for hall and version info
                hall = _extract_hall_info(showtime_element)
                version = _extract_version_info(showtime_element)
                
                # Format showtime string
                showtime_str = time_text
                if hall or version:
                    details = []
                    if hall:
                        details.append(hall)
                    if version:
                        details.append(version)
                    showtime_str += f" ({', '.join(details)})"
                
                showtimes.append(showtime_str)
                
            except Exception as e:
                logger.debug(f"Error extracting showtime: {e}")
                continue
    
    except Exception as e:
        logger.debug(f"Error in _extract_showtimes: {e}")
    
    return showtimes


def _extract_hall_info(element) -> Optional[str]:
    """Extract cinema hall information."""
    try:
        hall_selectors = [
            ".hall",
            ".cinema",
            ".saal",
            "[data-hall]",
            ".hall-info"
        ]
        
        for selector in hall_selectors:
            hall_element = element.query_selector(selector)
            if hall_element:
                hall_text = hall_element.text_content()
                if hall_text and hall_text.strip():
                    return hall_text.strip()
        
        # Check if element itself contains hall info
        element_text = element.text_content()
        if any(keyword in element_text.lower() for keyword in ['saal', 'cinema', 'hall']):
            # Try to extract hall number
            import re
            hall_match = re.search(r'(saal|cinema|hall)\s*(\d+)', element_text, re.IGNORECASE)
            if hall_match:
                return f"Cinema {hall_match.group(2)}"
    
    except Exception:
        pass
    
    return None


def _extract_version_info(element) -> Optional[str]:
    """Extract version information (OV/OmU)."""
    try:
        element_text = element.text_content()
        
        # Look for version indicators
        if 'OV' in element_text:
            return 'OV'
        elif 'OmU' in element_text:
            return 'OmU'
        elif 'Original' in element_text:
            return 'OV'
        
        # Check for version in parent or sibling elements
        version_selectors = [
            ".version",
            ".language",
            ".format",
            "[data-version]"
        ]
        
        for selector in version_selectors:
            version_element = element.query_selector(selector)
            if version_element:
                version_text = version_element.text_content()
                if version_text and version_text.strip():
                    return version_text.strip()
    
    except Exception:
        pass
    
    return None
