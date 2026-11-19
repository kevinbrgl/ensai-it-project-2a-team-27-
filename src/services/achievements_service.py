"""Service layer for achievement evaluation and trophy unlocking.

Computes unlocked and locked achievements based on aggregated user metrics.
"""

from dataclasses import dataclass
from typing import Literal

from src.dao.achievements_dao import AchievementDAO
from src.models.achievements import (
    Achievement,
    AchievementCategory,
    AchievementTier,
    AchievementUserStats,
)


@dataclass(frozen=True)
class AchievementDefinition:
    """Define an achievement milestone and its tracked metric.

    Attributes
    ----------
    id_achievement : str
        Stable achievement identifier.
    title : str
        Display title.
    description : str
        Description of the requirement.
    category : AchievementCategory
        Activity category.
    tier : AchievementTier
        Achievement tier.
    icon : str
        Icon displayed with the milestone.
    target : int
        Metric value required to reach the milestone.
    stat_key : str
        Key of the user statistic evaluated for this milestone.

    """

    id_achievement: str
    title: str
    description: str
    category: AchievementCategory
    tier: AchievementTier
    icon: str
    target: int
    stat_key: str

    def evaluate(self, current_stat: int) -> Achievement:
        """Evaluate milestone achievement against a current user metric.

        Parameters
        ----------
        current_stat : int
            Current metric count achieved by the user.

        Returns
        -------
        Achievement
            Evaluated Achievement schema instance.

        """
        bounded_stat = max(0, current_stat)
        bounded_target = max(1, self.target)
        is_unlocked = bounded_stat >= bounded_target
        progress = min(bounded_target, bounded_stat)
        percentage = round(
            min(100.0, (bounded_stat / bounded_target) * 100.0),
            1,
        )

        return Achievement(
            id_achievement=self.id_achievement,
            title=self.title,
            description=self.description,
            category=self.category,
            tier=self.tier,
            icon=self.icon,
            is_unlocked=is_unlocked,
            progress=progress,
            target=bounded_target,
            progress_percentage=percentage,
        )


ACHIEVEMENT_DEFINITIONS: tuple[AchievementDefinition, ...] = (
    AchievementDefinition(
        id_achievement="first_book",
        title="First Chapter",
        description="Finish your first book.",
        category=AchievementCategory.READING,
        tier=AchievementTier.BRONZE,
        icon="🌱",
        target=1,
        stat_key="completed_books",
    ),
    AchievementDefinition(
        id_achievement="apprentice_reader",
        title="Avid Reader",
        description="Finish 5 books.",
        category=AchievementCategory.READING,
        tier=AchievementTier.SILVER,
        icon="📖",
        target=5,
        stat_key="completed_books",
    ),
    AchievementDefinition(
        id_achievement="bookworm",
        title="Bookworm",
        description="Finish 10 books.",
        category=AchievementCategory.READING,
        tier=AchievementTier.SILVER,
        icon="👓",
        target=10,
        stat_key="completed_books",
    ),
    AchievementDefinition(
        id_achievement="bibliophile",
        title="Distinguished Bibliophile",
        description="Finish 15 books.",
        category=AchievementCategory.READING,
        tier=AchievementTier.GOLD,
        icon="📚",
        target=15,
        stat_key="completed_books",
    ),
    AchievementDefinition(
        id_achievement="voracious_reader",
        title="Voracious Reader",
        description="Finish 25 books.",
        category=AchievementCategory.READING,
        tier=AchievementTier.GOLD,
        icon="🔥",
        target=25,
        stat_key="completed_books",
    ),
    AchievementDefinition(
        id_achievement="half_century",
        title="Half-Century Club",
        description="Finish 50 books.",
        category=AchievementCategory.READING,
        tier=AchievementTier.PLATINUM,
        icon="🏅",
        target=50,
        stat_key="completed_books",
    ),
    AchievementDefinition(
        id_achievement="centurion",
        title="Centurion of the Shelves",
        description="Finish 100 books.",
        category=AchievementCategory.READING,
        tier=AchievementTier.PLATINUM,
        icon="🏆",
        target=100,
        stat_key="completed_books",
    ),
    AchievementDefinition(
        id_achievement="warming_up",
        title="Warming Up",
        description="Read 250 pages across the books you have finished.",
        category=AchievementCategory.READING,
        tier=AchievementTier.BRONZE,
        icon="🌅",
        target=250,
        stat_key="pages_read",
    ),
    AchievementDefinition(
        id_achievement="page_turner",
        title="Page Turner",
        description="Read 1,000 pages across the books you have finished.",
        category=AchievementCategory.READING,
        tier=AchievementTier.SILVER,
        icon="📜",
        target=1000,
        stat_key="pages_read",
    ),
    AchievementDefinition(
        id_achievement="page_devourer",
        title="Page Devourer",
        description="Read 2,500 pages across the books you have finished.",
        category=AchievementCategory.READING,
        tier=AchievementTier.GOLD,
        icon="📑",
        target=2500,
        stat_key="pages_read",
    ),
    AchievementDefinition(
        id_achievement="century_reader",
        title="Book Marathoner",
        description="Read 5,000 pages across the books you have finished.",
        category=AchievementCategory.READING,
        tier=AchievementTier.GOLD,
        icon="👑",
        target=5000,
        stat_key="pages_read",
    ),
    AchievementDefinition(
        id_achievement="ten_thousand_pages",
        title="Ten Thousand Pages",
        description="Read 10,000 pages across the books you have finished.",
        category=AchievementCategory.READING,
        tier=AchievementTier.PLATINUM,
        icon="⛰️",
        target=10000,
        stat_key="pages_read",
    ),
    AchievementDefinition(
        id_achievement="doorstopper",
        title="Doorstopper",
        description="Finish a book of 500 pages or more.",
        category=AchievementCategory.READING,
        tier=AchievementTier.SILVER,
        icon="🧱",
        target=500,
        stat_key="longest_book_pages",
    ),
    AchievementDefinition(
        id_achievement="tome_titan",
        title="Tome Titan",
        description="Finish a book of 800 pages or more.",
        category=AchievementCategory.READING,
        tier=AchievementTier.GOLD,
        icon="🏋️",
        target=800,
        stat_key="longest_book_pages",
    ),
    AchievementDefinition(
        id_achievement="juggler",
        title="Juggler",
        description="Have 3 books in progress at the same time.",
        category=AchievementCategory.READING,
        tier=AchievementTier.BRONZE,
        icon="🤹",
        target=3,
        stat_key="reading_books",
    ),
    AchievementDefinition(
        id_achievement="chronicler",
        title="Chronicler",
        description="Record the finish date of 5 books you have finished.",
        category=AchievementCategory.READING,
        tier=AchievementTier.BRONZE,
        icon="📅",
        target=5,
        stat_key="dated_books",
    ),
    AchievementDefinition(
        id_achievement="diarist",
        title="Meticulous Diarist",
        description="Record the finish date of 25 books you have finished.",
        category=AchievementCategory.READING,
        tier=AchievementTier.SILVER,
        icon="🗓️",
        target=25,
        stat_key="dated_books",
    ),
    AchievementDefinition(
        id_achievement="life_is_short",
        title="Life's Too Short",
        description="Set aside a book that wasn't for you.",
        category=AchievementCategory.READING,
        tier=AchievementTier.BRONZE,
        icon="🚪",
        target=1,
        stat_key="abandoned_books",
    ),
    AchievementDefinition(
        id_achievement="genre_curious",
        title="Curious Mind",
        description="Have books from 3 different genres in your library.",
        category=AchievementCategory.EXPLORATION,
        tier=AchievementTier.BRONZE,
        icon="🧭",
        target=3,
        stat_key="distinct_genres",
    ),
    AchievementDefinition(
        id_achievement="genre_hopper",
        title="Genre Hopper",
        description="Have books from 5 different genres in your library.",
        category=AchievementCategory.EXPLORATION,
        tier=AchievementTier.SILVER,
        icon="🔀",
        target=5,
        stat_key="distinct_genres",
    ),
    AchievementDefinition(
        id_achievement="literary_polymath",
        title="Literary Polymath",
        description="Have books from 7 different genres in your library.",
        category=AchievementCategory.EXPLORATION,
        tier=AchievementTier.GOLD,
        icon="🌍",
        target=7,
        stat_key="distinct_genres",
    ),
    AchievementDefinition(
        id_achievement="omnivore",
        title="Literary Omnivore",
        description="Have books from 12 different genres in your library.",
        category=AchievementCategory.EXPLORATION,
        tier=AchievementTier.PLATINUM,
        icon="✨",
        target=12,
        stat_key="distinct_genres",
    ),
    AchievementDefinition(
        id_achievement="new_voices",
        title="New Voices",
        description="Finish books by 5 different authors.",
        category=AchievementCategory.EXPLORATION,
        tier=AchievementTier.BRONZE,
        icon="🪶",
        target=5,
        stat_key="distinct_authors",
    ),
    AchievementDefinition(
        id_achievement="author_collector",
        title="Author Collector",
        description="Finish books by 15 different authors.",
        category=AchievementCategory.EXPLORATION,
        tier=AchievementTier.SILVER,
        icon="🪶",
        target=15,
        stat_key="distinct_authors",
    ),
    AchievementDefinition(
        id_achievement="literary_cartographer",
        title="Literary Cartographer",
        description="Finish books by 30 different authors.",
        category=AchievementCategory.EXPLORATION,
        tier=AchievementTier.GOLD,
        icon="🗺️",
        target=30,
        stat_key="distinct_authors",
    ),
    AchievementDefinition(
        id_achievement="timeless",
        title="Timeless Tale",
        description="Finish a book first published before 1950.",
        category=AchievementCategory.EXPLORATION,
        tier=AchievementTier.BRONZE,
        icon="⏳",
        target=1,
        stat_key="classics_read",
    ),
    AchievementDefinition(
        id_achievement="classicist",
        title="Classicist",
        description="Finish 5 books first published before 1950.",
        category=AchievementCategory.EXPLORATION,
        tier=AchievementTier.GOLD,
        icon="🏛️",
        target=5,
        stat_key="classics_read",
    ),
    AchievementDefinition(
        id_achievement="first_review",
        title="First Impressions",
        description="Write and publish your first review.",
        category=AchievementCategory.COMMUNITY,
        tier=AchievementTier.BRONZE,
        icon="✍️",
        target=1,
        stat_key="reviews_count",
    ),
    AchievementDefinition(
        id_achievement="literary_critic",
        title="Recognized Critic",
        description="Write 5 reviews.",
        category=AchievementCategory.COMMUNITY,
        tier=AchievementTier.SILVER,
        icon="🖋️",
        target=5,
        stat_key="reviews_count",
    ),
    AchievementDefinition(
        id_achievement="seasoned_critic",
        title="Seasoned Critic",
        description="Write 15 reviews.",
        category=AchievementCategory.COMMUNITY,
        tier=AchievementTier.GOLD,
        icon="💬",
        target=15,
        stat_key="reviews_count",
    ),
    AchievementDefinition(
        id_achievement="voice_of_the_library",
        title="Voice of the Library",
        description="Write 50 reviews.",
        category=AchievementCategory.COMMUNITY,
        tier=AchievementTier.PLATINUM,
        icon="📣",
        target=50,
        stat_key="reviews_count",
    ),
    AchievementDefinition(
        id_achievement="essayist",
        title="Essayist",
        description="Write 3 reviews of at least 200 characters.",
        category=AchievementCategory.COMMUNITY,
        tier=AchievementTier.SILVER,
        icon="📝",
        target=3,
        stat_key="detailed_reviews",
    ),
    AchievementDefinition(
        id_achievement="standing_ovation",
        title="Standing Ovation",
        description="Give a 5-star rating to 3 books.",
        category=AchievementCategory.COMMUNITY,
        tier=AchievementTier.BRONZE,
        icon="⭐",
        target=3,
        stat_key="five_star_reviews",
    ),
    AchievementDefinition(
        id_achievement="generous_heart",
        title="Generous Heart",
        description="Like 10 books.",
        category=AchievementCategory.COMMUNITY,
        tier=AchievementTier.BRONZE,
        icon="👍",
        target=10,
        stat_key="liked_books",
    ),
    AchievementDefinition(
        id_achievement="social_circle",
        title="Reading Circle",
        description="Follow 3 other readers.",
        category=AchievementCategory.SOCIAL,
        tier=AchievementTier.BRONZE,
        icon="🤝",
        target=3,
        stat_key="following_count",
    ),
    AchievementDefinition(
        id_achievement="well_connected",
        title="Well Connected",
        description="Follow 10 other readers.",
        category=AchievementCategory.SOCIAL,
        tier=AchievementTier.SILVER,
        icon="🔗",
        target=10,
        stat_key="following_count",
    ),
    AchievementDefinition(
        id_achievement="first_follower",
        title="First Follower",
        description="Gain your first follower.",
        category=AchievementCategory.SOCIAL,
        tier=AchievementTier.BRONZE,
        icon="🙋",
        target=1,
        stat_key="followers_count",
    ),
    AchievementDefinition(
        id_achievement="rising_star",
        title="Rising Star",
        description="Gain 5 followers.",
        category=AchievementCategory.SOCIAL,
        tier=AchievementTier.SILVER,
        icon="📈",
        target=5,
        stat_key="followers_count",
    ),
    AchievementDefinition(
        id_achievement="literary_influencer",
        title="Literary Influencer",
        description="Gain 25 followers.",
        category=AchievementCategory.SOCIAL,
        tier=AchievementTier.GOLD,
        icon="📡",
        target=25,
        stat_key="followers_count",
    ),
    AchievementDefinition(
        id_achievement="literary_icon",
        title="Literary Icon",
        description="Gain 50 followers.",
        category=AchievementCategory.SOCIAL,
        tier=AchievementTier.PLATINUM,
        icon="💎",
        target=50,
        stat_key="followers_count",
    ),
    AchievementDefinition(
        id_achievement="kindred_spirit",
        title="Kindred Spirit",
        description="Follow a reader who follows you back.",
        category=AchievementCategory.SOCIAL,
        tier=AchievementTier.BRONZE,
        icon="🫂",
        target=1,
        stat_key="mutual_follows",
    ),
    AchievementDefinition(
        id_achievement="book_club",
        title="Book Club",
        description="Follow 5 readers who follow you back.",
        category=AchievementCategory.SOCIAL,
        tier=AchievementTier.GOLD,
        icon="☕",
        target=5,
        stat_key="mutual_follows",
    ),
    AchievementDefinition(
        id_achievement="making_an_entrance",
        title="Making an Entrance",
        description="Complete your profile with a bio and a picture.",
        category=AchievementCategory.SOCIAL,
        tier=AchievementTier.BRONZE,
        icon="🪪",
        target=2,
        stat_key="profile_fields",
    ),
    AchievementDefinition(
        id_achievement="curator",
        title="Literary Curator",
        description="Create 2 playlists.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.BRONZE,
        icon="📁",
        target=2,
        stat_key="playlists_count",
    ),
    AchievementDefinition(
        id_achievement="master_curator",
        title="Master Curator",
        description="Create 5 playlists.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.SILVER,
        icon="🗂️",
        target=5,
        stat_key="playlists_count",
    ),
    AchievementDefinition(
        id_achievement="archivist",
        title="Archivist",
        description="Create 10 playlists.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.GOLD,
        icon="🗄️",
        target=10,
        stat_key="playlists_count",
    ),
    AchievementDefinition(
        id_achievement="grand_collection",
        title="Grand Collection",
        description="Put 10 books in a single playlist.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.SILVER,
        icon="📦",
        target=10,
        stat_key="largest_playlist",
    ),
    AchievementDefinition(
        id_achievement="treasured_shelf",
        title="Golden Shelf",
        description="Add 3 books to your favorites.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.BRONZE,
        icon="❤️",
        target=3,
        stat_key="favorites_count",
    ),
    AchievementDefinition(
        id_achievement="hall_of_fame",
        title="Hall of Fame",
        description="Add 10 books to your favorites.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.SILVER,
        icon="❤️",
        target=10,
        stat_key="favorites_count",
    ),
    AchievementDefinition(
        id_achievement="heart_of_the_library",
        title="Heart of the Library",
        description="Add 25 books to your favorites.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.GOLD,
        icon="❤️",
        target=25,
        stat_key="favorites_count",
    ),
    AchievementDefinition(
        id_achievement="home_library",
        title="Home Library",
        description="Have 10 books in your library.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.BRONZE,
        icon="🏠",
        target=10,
        stat_key="library_size",
    ),
    AchievementDefinition(
        id_achievement="growing_library",
        title="Growing Library",
        description="Have 50 books in your library.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.SILVER,
        icon="🏘️",
        target=50,
        stat_key="library_size",
    ),
    AchievementDefinition(
        id_achievement="grand_library",
        title="Grand Library",
        description="Have 100 books in your library.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.GOLD,
        icon="🏰",
        target=100,
        stat_key="library_size",
    ),
    AchievementDefinition(
        id_achievement="library_of_legends",
        title="Library of Legends",
        description="Have 250 books in your library.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.PLATINUM,
        icon="🌌",
        target=250,
        stat_key="library_size",
    ),
    AchievementDefinition(
        id_achievement="bottomless_tbr",
        title="Bottomless Reading List",
        description="Add 10 books to your Want to Read list.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.BRONZE,
        icon="🔖",
        target=10,
        stat_key="want_to_read_books",
    ),
)


class AchievementService:
    """Evaluate achievement milestones for users.

    Attributes
    ----------
    dao : AchievementDAO
        Associated AchievementDAO instance.

    """

    def __init__(self, achievement_dao: AchievementDAO) -> None:
        """Initialize AchievementService with an AchievementDAO.

        Parameters
        ----------
        achievement_dao : AchievementDAO
            DAO used to retrieve user statistics.

        """
        self.dao = achievement_dao

    def get_achievements(
        self,
        user_id: int,
        status_filter: Literal["all", "unlocked", "locked"] = "all",
    ) -> list[Achievement]:
        """Get the list of achievements and unlock status for a user.

        Parameters
        ----------
        user_id : int
            ID of the user.
        status_filter : {'all', 'unlocked', 'locked'}, optional
            Which unlock status to include. By default, include all
            achievements.

        Returns
        -------
        list[Achievement]
            List of evaluated Achievement schemas.

        """
        stats: AchievementUserStats = self.dao.get_user_stats(user_id)
        stats_dict = stats.model_dump()

        all_achievements: list[Achievement] = [
            defn.evaluate(current_stat=stats_dict.get(defn.stat_key, 0))
            for defn in ACHIEVEMENT_DEFINITIONS
        ]

        if status_filter == "unlocked":
            return [a for a in all_achievements if a.is_unlocked]
        if status_filter == "locked":
            return [a for a in all_achievements if not a.is_unlocked]
        return all_achievements
