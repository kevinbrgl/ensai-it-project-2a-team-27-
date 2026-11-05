"""Unit tests for StatsService.

The StatsDAO is replaced by a mock: no database is needed.
"""

from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from src.dao.stats_dao import StatsDAO
from src.models.stats import GenreCount, RatingCount, UserStats
from src.services.stats_service import StatsService

ID_USER = 1


@pytest.fixture
def mock_dao(mocker: MockerFixture) -> Mock:
    """Return a fake StatsDAO with the same methods as the real one."""
    dao = mocker.Mock(spec=StatsDAO)
    dao.count_finished_books.return_value = 0
    dao.count_genres.return_value = []
    dao.count_ratings.return_value = {}
    return dao


@pytest.fixture
def service(mock_dao: Mock) -> StatsService:
    """Return a StatsService using the mocked DAO."""
    return StatsService(mock_dao)


class TestGetStats:
    """Tests for StatsService.get_stats."""

    def test_assembles_the_statistics(
        self,
        service: StatsService,
        mock_dao: Mock,
    ) -> None:
        """The three statistics of the DAO are put together."""
        genres = [GenreCount(category="Fantasy", count=2)]
        mock_dao.count_finished_books.return_value = 3
        mock_dao.count_genres.return_value = genres
        mock_dao.count_ratings.return_value = {4: 2, 5: 1}

        result = service.get_stats(ID_USER)

        assert result == UserStats(
            books_finished=3,
            genres=genres,
            ratings=[
                RatingCount(rating=1, count=0),
                RatingCount(rating=2, count=0),
                RatingCount(rating=3, count=0),
                RatingCount(rating=4, count=2),
                RatingCount(rating=5, count=1),
            ],
        )

    def test_no_reviews_gives_five_zero_ratings(
        self,
        service: StatsService,
    ) -> None:
        """Without reviews, the five ratings are listed with a count of 0."""
        result = service.get_stats(ID_USER)

        assert [(r.rating, r.count) for r in result.ratings] == [
            (1, 0),
            (2, 0),
            (3, 0),
            (4, 0),
            (5, 0),
        ]

    def test_dao_called_for_the_user(
        self,
        service: StatsService,
        mock_dao: Mock,
    ) -> None:
        """Each statistic is asked once, for the given user."""
        service.get_stats(ID_USER)

        mock_dao.count_finished_books.assert_called_once_with(ID_USER)
        mock_dao.count_genres.assert_called_once_with(ID_USER)
        mock_dao.count_ratings.assert_called_once_with(ID_USER)
