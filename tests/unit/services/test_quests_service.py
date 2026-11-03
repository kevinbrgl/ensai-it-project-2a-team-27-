"""Unit tests for QuestService.

Validates progress calculation, bounding, completion status,
and filtering without database access.
"""

from unittest.mock import Mock

import pytest

from src.dao.quests_dao import QuestDAO
from src.models.quests import QuestCategory, QuestUserStats
from src.services.quests_service import QuestService

ID_USER = 1
PERCENT_ZERO = 0.0
PERCENT_FULL = 100.0
PERCENT_HALF = 50.0
PERCENT_THIRD = 33.3
TOTAL_QUESTS_COUNT = 6


@pytest.fixture
def mock_dao() -> Mock:
    """Return a mocked QuestDAO."""
    return Mock(spec=QuestDAO)


@pytest.fixture
def service(mock_dao: Mock) -> QuestService:
    """Return a QuestService wired with the mocked DAO."""
    return QuestService(mock_dao)


class TestQuestService:
    """Tests for QuestService.get_quests."""

    def test_zero_stats_all_uncompleted(
        self,
        service: QuestService,
        mock_dao: Mock,
    ) -> None:
        """When user stats are all zero, all quests have 0% progress."""
        mock_dao.get_user_stats.return_value = QuestUserStats(
            completed_books=0,
            reading_books=0,
            distinct_categories=0,
            following_count=0,
            favorite_books=0,
        )

        quests = service.get_quests(ID_USER, status_filter="all")

        assert len(quests) == TOTAL_QUESTS_COUNT
        for q in quests:
            assert q.current == 0
            assert q.progress_percentage == pytest.approx(PERCENT_ZERO)
            assert q.is_completed is False
        mock_dao.get_user_stats.assert_called_once_with(ID_USER)

    def test_partial_progress_calculation(
        self,
        service: QuestService,
        mock_dao: Mock,
    ) -> None:
        """Partial progress correctly computes percentage and completion."""
        mock_dao.get_user_stats.return_value = QuestUserStats(
            completed_books=1,
            reading_books=1,
            distinct_categories=1,
            following_count=1,
            favorite_books=0,
        )

        quests = service.get_quests(ID_USER, status_filter="all")
        by_id = {q.id_quest: q for q in quests}

        # read_first_book (target 1): completed
        assert by_id["read_first_book"].is_completed is True
        assert by_id["read_first_book"].progress_percentage == pytest.approx(
            PERCENT_FULL,
        )

        # reading_marathon (target 3): 1/3 = 33.3%
        assert by_id["reading_marathon"].is_completed is False
        assert by_id["reading_marathon"].progress_percentage == pytest.approx(
            PERCENT_THIRD,
        )

        # cercle_litteraire (target 2): 1/2 = 50.0%
        assert by_id["cercle_litteraire"].is_completed is False
        assert by_id["cercle_litteraire"].progress_percentage == pytest.approx(
            PERCENT_HALF,
        )

    def test_capped_progress_exceeding_target(
        self,
        service: QuestService,
        mock_dao: Mock,
    ) -> None:
        """Progress exceeding target is capped at 100%."""
        mock_dao.get_user_stats.return_value = QuestUserStats(
            completed_books=10,
            reading_books=5,
            distinct_categories=5,
            following_count=10,
            favorite_books=5,
        )

        quests = service.get_quests(ID_USER, status_filter="all")

        for q in quests:
            assert q.is_completed is True
            assert q.progress_percentage == pytest.approx(PERCENT_FULL)

    def test_filter_active_quests(
        self,
        service: QuestService,
        mock_dao: Mock,
    ) -> None:
        """Filtering by active returns only uncompleted quests."""
        mock_dao.get_user_stats.return_value = QuestUserStats(
            completed_books=1,
            reading_books=0,
            distinct_categories=0,
            following_count=0,
            favorite_books=0,
        )

        active = service.get_quests(ID_USER, status_filter="active")

        # read_first_book is completed (target 1), so not in active
        assert all(not q.is_completed for q in active)
        active_ids = {q.id_quest for q in active}
        assert "read_first_book" not in active_ids
        assert "reading_marathon" in active_ids

    def test_filter_completed_quests(
        self,
        service: QuestService,
        mock_dao: Mock,
    ) -> None:
        """Filtering by completed returns only completed quests."""
        mock_dao.get_user_stats.return_value = QuestUserStats(
            completed_books=1,
            reading_books=0,
            distinct_categories=0,
            following_count=0,
            favorite_books=0,
        )

        completed = service.get_quests(ID_USER, status_filter="completed")

        assert len(completed) == 1
        assert completed[0].id_quest == "read_first_book"
        assert completed[0].is_completed is True

    def test_quest_categories_represented(
        self,
        service: QuestService,
        mock_dao: Mock,
    ) -> None:
        """All defined quest categories are represented in the set."""
        mock_dao.get_user_stats.return_value = QuestUserStats(
            completed_books=0,
            reading_books=0,
            distinct_categories=0,
            following_count=0,
            favorite_books=0,
        )

        quests = service.get_quests(ID_USER)
        categories = {q.category for q in quests}

        assert QuestCategory.READING in categories
        assert QuestCategory.EXPLORATION in categories
        assert QuestCategory.SOCIAL in categories
        assert QuestCategory.ENGAGEMENT in categories
