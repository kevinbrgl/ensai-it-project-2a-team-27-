"""Unit tests for AchievementService.

Validates progress calculation, bounding, unlock status,
and filtering without database access.
"""

from unittest.mock import Mock

import pytest

from src.dao.achievements_dao import AchievementDAO
from src.models.achievements import (
    AchievementCategory,
    AchievementTier,
    AchievementUserStats,
)
from src.services.achievements_service import (
    ACHIEVEMENT_DEFINITIONS,
    AchievementService,
)

ID_USER = 1
PERCENT_ZERO = 0.0
PERCENT_FULL = 100.0
PERCENT_HALF = 50.0
PERCENT_TWENTY = 20.0
EXPECTED_PROGRESS_PAGES = 200
TOTAL_ACHIEVEMENTS_COUNT = 55
MAX_PROFILE_FIELDS = 2
LARGE_STAT = 100_000


@pytest.fixture
def mock_dao() -> Mock:
    """Return a mocked AchievementDAO."""
    return Mock(spec=AchievementDAO)


@pytest.fixture
def service(mock_dao: Mock) -> AchievementService:
    """Return an AchievementService wired with the mocked DAO."""
    return AchievementService(mock_dao)


class TestAchievementService:
    """Tests for AchievementService.get_achievements."""

    def test_zero_stats_all_locked(
        self,
        service: AchievementService,
        mock_dao: Mock,
    ) -> None:
        """When user stats are all zero, all achievements are locked."""
        mock_dao.get_user_stats.return_value = AchievementUserStats(
            completed_books=0,
            pages_read=0,
            distinct_genres=0,
            reviews_count=0,
            favorites_count=0,
            following_count=0,
            followers_count=0,
            playlists_count=0,
        )

        achievements = service.get_achievements(
            ID_USER,
            status_filter="all",
        )

        assert len(achievements) == TOTAL_ACHIEVEMENTS_COUNT
        for a in achievements:
            assert a.progress == 0
            assert a.progress_percentage == pytest.approx(PERCENT_ZERO)
            assert a.is_unlocked is False
        mock_dao.get_user_stats.assert_called_once_with(ID_USER)

    def test_partial_progress_and_unlock_calculation(
        self,
        service: AchievementService,
        mock_dao: Mock,
    ) -> None:
        """Partial progress correctly computes percentage and unlock state."""
        mock_dao.get_user_stats.return_value = AchievementUserStats(
            completed_books=1,
            pages_read=200,
            distinct_genres=1,
            reviews_count=1,
            favorites_count=0,
            following_count=0,
            followers_count=0,
            playlists_count=1,
        )

        achievements = service.get_achievements(
            ID_USER,
            status_filter="all",
        )
        by_id = {a.id_achievement: a for a in achievements}

        # first_book (target 1): unlocked
        assert by_id["first_book"].is_unlocked is True
        assert by_id["first_book"].progress == 1
        assert by_id["first_book"].progress_percentage == pytest.approx(
            PERCENT_FULL,
        )

        # apprentice_reader (target 5): 1/5 = 20.0%
        assert by_id["apprentice_reader"].is_unlocked is False
        assert by_id["apprentice_reader"].progress == 1
        assert by_id["apprentice_reader"].progress_percentage == pytest.approx(
            PERCENT_TWENTY,
        )

        # page_turner (target 1000): 200/1000 = 20.0%
        assert by_id["page_turner"].is_unlocked is False
        assert by_id["page_turner"].progress == EXPECTED_PROGRESS_PAGES
        assert by_id["page_turner"].progress_percentage == pytest.approx(
            PERCENT_TWENTY,
        )

        # first_review (target 1): unlocked
        assert by_id["first_review"].is_unlocked is True
        assert by_id["first_review"].progress == 1

        # curator (target 2): 1/2 = 50.0%
        assert by_id["curator"].is_unlocked is False
        assert by_id["curator"].progress == 1
        assert by_id["curator"].progress_percentage == pytest.approx(
            PERCENT_HALF,
        )

    def test_capped_progress_exceeding_target(
        self,
        service: AchievementService,
        mock_dao: Mock,
    ) -> None:
        """Progress exceeding target is capped at target and 100%."""
        mock_dao.get_user_stats.return_value = AchievementUserStats(
            **{
                name: MAX_PROFILE_FIELDS
                if name == "profile_fields"
                else LARGE_STAT
                for name in AchievementUserStats.model_fields
            },
        )

        achievements = service.get_achievements(
            ID_USER,
            status_filter="all",
        )

        for a in achievements:
            assert a.is_unlocked is True
            assert a.progress == a.target
            assert a.progress_percentage == pytest.approx(PERCENT_FULL)

    def test_filter_unlocked_achievements(
        self,
        service: AchievementService,
        mock_dao: Mock,
    ) -> None:
        """Filtering by unlocked returns only unlocked milestones."""
        mock_dao.get_user_stats.return_value = AchievementUserStats(
            completed_books=1,
            pages_read=50,
            distinct_genres=0,
            reviews_count=0,
            favorites_count=0,
            following_count=0,
            followers_count=0,
            playlists_count=0,
        )

        unlocked = service.get_achievements(
            ID_USER,
            status_filter="unlocked",
        )

        assert len(unlocked) == 1
        assert unlocked[0].id_achievement == "first_book"
        assert unlocked[0].is_unlocked is True

    def test_filter_locked_achievements(
        self,
        service: AchievementService,
        mock_dao: Mock,
    ) -> None:
        """Filtering by locked returns only locked milestones."""
        mock_dao.get_user_stats.return_value = AchievementUserStats(
            completed_books=1,
            pages_read=50,
            distinct_genres=0,
            reviews_count=0,
            favorites_count=0,
            following_count=0,
            followers_count=0,
            playlists_count=0,
        )

        locked = service.get_achievements(
            ID_USER,
            status_filter="locked",
        )

        assert len(locked) == TOTAL_ACHIEVEMENTS_COUNT - 1
        assert all(not a.is_unlocked for a in locked)
        locked_ids = {a.id_achievement for a in locked}
        assert "first_book" not in locked_ids
        assert "apprentice_reader" in locked_ids

    def test_achievement_categories_and_tiers_represented(
        self,
        service: AchievementService,
        mock_dao: Mock,
    ) -> None:
        """All defined categories and tiers are represented in the set."""
        mock_dao.get_user_stats.return_value = AchievementUserStats(
            completed_books=0,
            pages_read=0,
            distinct_genres=0,
            reviews_count=0,
            favorites_count=0,
            following_count=0,
            followers_count=0,
            playlists_count=0,
        )

        achievements = service.get_achievements(ID_USER)
        categories = {a.category for a in achievements}
        tiers = {a.tier for a in achievements}

        assert AchievementCategory.READING in categories
        assert AchievementCategory.EXPLORATION in categories
        assert AchievementCategory.COMMUNITY in categories
        assert AchievementCategory.SOCIAL in categories
        assert AchievementCategory.COLLECTION in categories

        assert AchievementTier.BRONZE in tiers
        assert AchievementTier.SILVER in tiers
        assert AchievementTier.GOLD in tiers
        assert AchievementTier.PLATINUM in tiers


TIER_RANK = {
    AchievementTier.BRONZE: 0,
    AchievementTier.SILVER: 1,
    AchievementTier.GOLD: 2,
    AchievementTier.PLATINUM: 3,
}


class TestAchievementCatalog:
    """Consistency checks on the achievement definitions."""

    def test_ids_are_unique(self) -> None:
        """No two achievements share an identifier."""
        ids = [defn.id_achievement for defn in ACHIEVEMENT_DEFINITIONS]

        assert len(ids) == len(set(ids))

    def test_stat_keys_exist(self) -> None:
        """Every achievement tracks a metric that the DAO actually provides."""
        fields = set(AchievementUserStats.model_fields)

        for defn in ACHIEVEMENT_DEFINITIONS:
            assert defn.stat_key in fields, defn.id_achievement

    def test_tiers_grow_with_targets(self) -> None:
        """For one metric, a harder milestone never has a lower tier."""
        by_stat: dict[str, list[tuple[int, int]]] = {}
        for defn in ACHIEVEMENT_DEFINITIONS:
            by_stat.setdefault(defn.stat_key, []).append(
                (defn.target, TIER_RANK[defn.tier]),
            )

        for stat_key, ladder in by_stat.items():
            ranks = [rank for _, rank in sorted(ladder)]
            assert ranks == sorted(ranks), stat_key
