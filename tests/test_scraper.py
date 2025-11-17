"""
Unit tests for the movie scraper functionality.
Tests are written before implementation following TDD approach.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from typing import Dict, List, Any

# Import from our new modular structure
from kinoweek.scraper import scrape_movies
from kinoweek.notifier import format_message, send_telegram, notify
from kinoweek.main import run_scraper, main


class TestScrapeMovies:
    """Test the core scraping functionality."""

    def test_scrape_movies_returns_dict(self):
        """Test that scrape_movies returns a dictionary with expected structure."""
        result = scrape_movies()
        assert isinstance(result, dict)

    def test_scrape_movies_has_correct_data_structure(self):
        """Test that returned data has correct nested structure with metadata."""
        result = scrape_movies()
        for date, movies in result.items():
            assert isinstance(date, str)
            assert isinstance(movies, dict)
            for title, movie_data in movies.items():
                assert isinstance(title, str)
                assert isinstance(movie_data, dict)
                assert 'info' in movie_data
                assert 'showtimes' in movie_data
                assert hasattr(movie_data['info'], 'title')
                assert isinstance(movie_data['showtimes'], list)

    @patch('kinoweek.scraper.httpx.Client')
    def test_scrape_movies_handles_api_errors(self, mock_client):
        """Test that API errors are handled gracefully."""
        mock_client.return_value.__enter__.return_value.get.side_effect = Exception("API failed")
        with pytest.raises(Exception):
            scrape_movies()


class TestFormatMessage:
    """Test the message formatting functionality."""

    def test_format_message_returns_string(self):
        """Test that format_message returns a string."""
        from kinoweek.scraper import MovieInfo, Showtime
        from datetime import datetime

        movie_info = MovieInfo(title="Wicked", duration=120, rating=12, year=2024, country="US")
        showtime = Showtime(datetime.fromisoformat("2024-11-24T19:30:00"), "19:30", "Sprache: Englisch")
        test_data = {"Mon 24.11": {"Wicked": {"info": movie_info, "showtimes": [showtime]}}}
        result = format_message(test_data)
        assert isinstance(result, str)

    def test_format_message_includes_all_data(self):
        """Test that formatted message includes all movie data."""
        from kinoweek.scraper import MovieInfo, Showtime
        from datetime import datetime

        wicked_info = MovieInfo(title="Wicked", duration=120, rating=12, year=2024, country="US")
        dune_info = MovieInfo(title="Dune", duration=166, rating=12, year=2024, country="US")
        wicked_st1 = Showtime(datetime.fromisoformat("2024-11-24T19:30:00"), "19:30", "Sprache: Englisch")
        wicked_st2 = Showtime(datetime.fromisoformat("2024-11-24T16:45:00"), "16:45", "Sprache: Englisch, Untertitel: Deutsch")
        dune_st = Showtime(datetime.fromisoformat("2024-11-24T20:00:00"), "20:00", "Sprache: Englisch")

        test_data = {
            "Mon 24.11": {
                "Wicked": {"info": wicked_info, "showtimes": [wicked_st1, wicked_st2]},
                "Dune": {"info": dune_info, "showtimes": [dune_st]}
            }
        }
        result = format_message(test_data)
        assert "Mon 24.11" in result
        assert "Wicked" in result
        assert "19:30" in result
        assert "Dune" in result

    def test_format_message_handles_empty_data(self):
        """Test that empty data is handled gracefully."""
        test_data = {}
        result = format_message(test_data)
        assert isinstance(result, str)
        assert "No movies found" in result

    def test_format_message_respects_telegram_limits(self):
        """Test that formatted message doesn't exceed Telegram limits."""
        from kinoweek.scraper import MovieInfo, Showtime
        from datetime import datetime

        movie_info = MovieInfo(title="A" * 50, duration=120, rating=12, year=2024, country="US")
        showtimes = [Showtime(datetime.fromisoformat("2024-11-24T19:30:00"), "19:30", "Sprache: Englisch")] * 1000
        test_data = {"Mon 24.11": {"Long Movie Title": {"info": movie_info, "showtimes": showtimes}}}
        result = format_message(test_data)
        assert len(result) <= 4096  # Telegram message limit


class TestSendTelegram:
    """Test the Telegram notification functionality."""

    @patch('kinoweek.notifier.httpx.Client')
    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token', 'TELEGRAM_CHAT_ID': 'test_chat'})
    def test_send_telegram_makes_api_call(self, mock_client):
        """Test that send_telegram makes correct API call."""
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        message = "Test message"
        result = send_telegram(message)

        mock_client.return_value.__enter__.return_value.post.assert_called_once()
        assert result is True

    @patch('kinoweek.notifier.httpx.Client')
    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token', 'TELEGRAM_CHAT_ID': 'test_chat'})
    def test_send_telegram_handles_api_error(self, mock_client):
        """Test that API errors are handled properly."""
        mock_response = Mock()
        mock_response.json.return_value = {"ok": False, "error": "Bad request"}
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        message = "Test message"
        result = send_telegram(message)
        assert result is False

    @patch('kinoweek.notifier.httpx.Client')
    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token', 'TELEGRAM_CHAT_ID': 'test_chat'})
    def test_send_telegram_handles_network_error(self, mock_client):
        """Test that network errors are handled properly."""
        mock_client.return_value.__enter__.return_value.post.side_effect = Exception("Network error")

        message = "Test message"
        result = send_telegram(message)
        assert result is False

    @patch.dict('os.environ', {}, clear=True)
    def test_send_telegram_requires_env_vars(self):
        """Test that environment variables are required."""
        with pytest.raises(Exception):
            send_telegram("test")


class TestIntegration:
    """Integration tests for the complete workflow."""

    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test_token', 'TELEGRAM_CHAT_ID': 'test_chat'})
    @patch('kinoweek.main.notify')
    @patch('kinoweek.main.scrape_movies')
    def test_full_workflow(self, mock_scrape, mock_notify):
        """Test the complete scraping and notification workflow."""
        from kinoweek.scraper import MovieInfo, Showtime
        from datetime import datetime

        movie_info = MovieInfo(title="Wicked", duration=120, rating=12, year=2024, country="US")
        showtime = Showtime(datetime.fromisoformat("2024-11-24T19:30:00"), "19:30", "Sprache: Englisch")
        mock_scrape.return_value = {"Mon 24.11": {"Wicked": {"info": movie_info, "showtimes": [showtime]}}}
        mock_notify.return_value = True

        # Test the main() function
        result = run_scraper(local_only=False)
        assert result is True
        mock_scrape.assert_called_once()
        mock_notify.assert_called_once()


class TestDataValidation:
    """Test data validation and edge cases."""

    def test_validate_movie_data_structure(self):
        """Test validation of movie data structure."""
        # valid_data = {"Mon 24.11": {"Wicked": ["19:30 (Cinema 10, 2D OV)"]}}
        # invalid_data = {"invalid": "structure"}

        # assert validate_movie_data(valid_data) is True
        # assert validate_movie_data(invalid_data) is False
        pytest.skip("Validation function not implemented yet")

    def test_handle_missing_website_elements(self):
        """Test handling of missing website elements."""
        # This would test the scraper's robustness
        pytest.skip("Scraper not implemented yet")

    def test_handle_empty_schedule(self):
        """Test handling of empty movie schedule."""
        # Test when no movies are found for a day
        pytest.skip("Scraper not implemented yet")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
