"""Unit tests for GenreWheelService.

Validates weighting formula, favorite bonuses, significance filtering,
color resolution, and percentage normalization.
"""

from unittest.mock import Mock

import pytest

from src.dao.genre_wheel_dao import GenreWheelDAO
from src.services.genre_wheel_service import (
    DEFAULT_EMPTY_COLOR,
    GenreWheelService,
)

ID_USER = 1
PERCENT_FULL = 100.0
PERCENT_THIRD = 33.3
EXPECTED_RATING_FIVE = 5.0
EXPECTED_THREE_GENRES = 3
HEX_COLOR_LENGTH = 7


@pytest.fixture
def mock_dao() -> Mock:
    """Return a mocked GenreWheelDAO."""
    return Mock(spec=GenreWheelDAO)


@pytest.fixture
def service(mock_dao: Mock) -> GenreWheelService:
    """Return a GenreWheelService wired with the mocked DAO."""
    return GenreWheelService(mock_dao)


class TestGenreWheelService:
    """Unit tests for GenreWheelService methods."""

    def test_empty_user_returns_empty_wheel(
        self,
        service: GenreWheelService,
        mock_dao: Mock,
    ) -> None:
        """User with no completed books returns empty wheel state."""
        mock_dao.get_user_completed_books.return_value = []

        wheel = service.get_genre_wheel(ID_USER)

        assert wheel.id_user == ID_USER
        assert wheel.is_empty is True
        assert wheel.total_books == 0
        assert wheel.empty_color == DEFAULT_EMPTY_COLOR
        assert wheel.segments == []
        mock_dao.get_user_completed_books.assert_called_once_with(ID_USER)

    def test_books_without_valid_category_skipped(
        self,
        service: GenreWheelService,
        mock_dao: Mock,
    ) -> None:
        """Books with empty or whitespace-only category are skipped."""
        mock_dao.get_user_completed_books.return_value = [
            {"id_book": 1, "category": "", "rating": 5, "is_favorite": False},
            {
                "id_book": 2,
                "category": "   ",
                "rating": 4,
                "is_favorite": False,
            },
        ]

        wheel = service.get_genre_wheel(ID_USER)

        assert wheel.is_empty is True
        assert wheel.segments == []

    def test_single_genre_gets_hundred_percent(
        self,
        service: GenreWheelService,
        mock_dao: Mock,
    ) -> None:
        """Single completed read genre occupies 100% of the wheel."""
        mock_dao.get_user_completed_books.return_value = [
            {
                "id_book": 10,
                "category": "Romance",
                "rating": 5,
                "is_favorite": True,
            },
        ]

        wheel = service.get_genre_wheel(ID_USER)

        assert wheel.is_empty is False
        assert wheel.total_books == 1
        assert len(wheel.segments) == 1

        seg = wheel.segments[0]
        assert seg.genre == "Romance"
        assert seg.color == "#F43F5E"
        assert seg.percentage == pytest.approx(PERCENT_FULL)
        assert seg.book_count == 1
        assert seg.average_rating == pytest.approx(EXPECTED_RATING_FIVE)

    def test_user_scenario_heavily_weighted_vs_disliked(
        self,
        service: GenreWheelService,
        mock_dao: Mock,
    ) -> None:
        """1 bad SF read vs 2 loved Romance reads filters out SF share."""
        mock_dao.get_user_completed_books.return_value = [
            {
                "id_book": 1,
                "category": "Science-Fiction",
                "rating": 1,
                "is_favorite": False,
            },
            {
                "id_book": 2,
                "category": "Romance",
                "rating": 5,
                "is_favorite": False,
            },
            {
                "id_book": 3,
                "category": "Romance",
                "rating": 5,
                "is_favorite": True,
            },
        ]

        wheel = service.get_genre_wheel(ID_USER)

        assert wheel.is_empty is False
        # Science-Fiction with weight 0.1 is < 3% share and gets filtered
        genre_names = [s.genre for s in wheel.segments]
        assert "Romance" in genre_names
        assert "Science-Fiction" not in genre_names
        assert wheel.segments[0].percentage == pytest.approx(PERCENT_FULL)

    def test_three_balanced_genres(
        self,
        service: GenreWheelService,
        mock_dao: Mock,
    ) -> None:
        """Three equal genres divide the wheel into thirds totaling 100%."""
        mock_dao.get_user_completed_books.return_value = [
            {
                "id_book": 1,
                "category": "Science-Fiction",
                "rating": 4,
                "is_favorite": False,
            },
            {
                "id_book": 2,
                "category": "Romance",
                "rating": 4,
                "is_favorite": False,
            },
            {
                "id_book": 3,
                "category": "Fantasy",
                "rating": 4,
                "is_favorite": False,
            },
        ]

        wheel = service.get_genre_wheel(ID_USER)

        assert len(wheel.segments) == EXPECTED_THREE_GENRES
        total_pct = sum(s.percentage for s in wheel.segments)
        assert total_pct == pytest.approx(PERCENT_FULL)
        for s in wheel.segments:
            assert s.percentage == pytest.approx(PERCENT_THIRD, abs=0.5)

    def test_unrated_book_receives_neutral_weight(
        self,
        service: GenreWheelService,
        mock_dao: Mock,
    ) -> None:
        """Unrated finished book is given baseline weight without rating."""
        mock_dao.get_user_completed_books.return_value = [
            {
                "id_book": 1,
                "category": "Thriller",
                "rating": None,
                "is_favorite": False,
            },
        ]

        wheel = service.get_genre_wheel(ID_USER)

        assert len(wheel.segments) == 1
        seg = wheel.segments[0]
        assert seg.average_rating is None
        assert seg.percentage == pytest.approx(PERCENT_FULL)

    def test_resolve_color_known_and_fallback(
        self,
    ) -> None:
        """Known genres use curated colors while custom genres use palette."""
        assert GenreWheelService.resolve_color("Romance") == "#F43F5E"
        assert GenreWheelService.resolve_color("SCI-FI") == "#8B5CF6"
        assert GenreWheelService.resolve_color("horror") == "#DC2626"

        custom_color = GenreWheelService.resolve_color("UnknownSubGenreX")
        assert custom_color.startswith("#")
        assert len(custom_color) == HEX_COLOR_LENGTH
