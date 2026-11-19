"""Service layer for quest management and progress evaluation.

Computes active quests and user progress based on DAO stats.
"""

from dataclasses import dataclass
from typing import Literal

from src.dao.quests_dao import QuestDAO
from src.models.quests import Quest, QuestCategory, QuestUserStats


@dataclass(frozen=True)
class QuestDefinition:
    """Define a quest and its tracked metric.

    Attributes
    ----------
    id_quest : str
        Stable quest identifier.
    title : str
        Display title.
    description : str
        Description of the requirement.
    category : QuestCategory
        Activity category.
    target : int
        Metric value required to reach the milestone.
    reward_xp : int
        Experience points awarded for completing the quest.
    stat_key : str
        Key of the user statistic evaluated for this milestone.

    """

    id_quest: str
    title: str
    description: str
    category: QuestCategory
    target: int
    reward_xp: int
    stat_key: str

    def evaluate(self, current: int) -> Quest:
        """Evaluate quest progress against a current metric value.

        Parameters
        ----------
        current : int
            Current value achieved by the user.

        Returns
        -------
        Quest
            Evaluated Quest schema instance.

        """
        bounded_current = max(0, current)
        bounded_target = max(1, self.target)
        is_completed = bounded_current >= bounded_target
        percentage = round(
            min(100.0, (bounded_current / bounded_target) * 100.0),
            1,
        )

        return Quest(
            id_quest=self.id_quest,
            title=self.title,
            description=self.description,
            category=self.category,
            current=bounded_current,
            target=bounded_target,
            progress_percentage=percentage,
            is_completed=is_completed,
            reward_xp=self.reward_xp,
        )


QUEST_DEFINITIONS: tuple[QuestDefinition, ...] = (
    QuestDefinition(
        id_quest="read_first_book",
        title="Turn the First Page",
        description="Finish your first book.",
        category=QuestCategory.READING,
        target=1,
        reward_xp=25,
        stat_key="completed_books",
    ),
    QuestDefinition(
        id_quest="currently_reading",
        title="In the Thick of It",
        description="Start reading a book.",
        category=QuestCategory.READING,
        target=1,
        reward_xp=15,
        stat_key="reading_books",
    ),
    QuestDefinition(
        id_quest="double_feature",
        title="Double Feature",
        description="Have 2 books in progress at the same time.",
        category=QuestCategory.READING,
        target=2,
        reward_xp=20,
        stat_key="reading_books",
    ),
    QuestDefinition(
        id_quest="reading_marathon",
        title="Hat Trick",
        description="Finish 3 books.",
        category=QuestCategory.READING,
        target=3,
        reward_xp=50,
        stat_key="completed_books",
    ),
    QuestDefinition(
        id_quest="high_five",
        title="High Five",
        description="Finish 5 books.",
        category=QuestCategory.READING,
        target=5,
        reward_xp=75,
        stat_key="completed_books",
    ),
    QuestDefinition(
        id_quest="ten_book_challenge",
        title="Ten-Book Challenge",
        description="Finish 10 books.",
        category=QuestCategory.READING,
        target=10,
        reward_xp=120,
        stat_key="completed_books",
    ),
    QuestDefinition(
        id_quest="five_hundred_pages",
        title="Five Hundred Pages",
        description="Read 500 pages across the books you have finished.",
        category=QuestCategory.READING,
        target=500,
        reward_xp=40,
        stat_key="pages_read",
    ),
    QuestDefinition(
        id_quest="two_thousand_pages",
        title="Two Thousand Pages",
        description="Read 2,000 pages across the books you have finished.",
        category=QuestCategory.READING,
        target=2000,
        reward_xp=100,
        stat_key="pages_read",
    ),
    QuestDefinition(
        id_quest="genre_explorer",
        title="Genre Explorer",
        description="Have books from 2 different genres in your library.",
        category=QuestCategory.EXPLORATION,
        target=2,
        reward_xp=40,
        stat_key="distinct_categories",
    ),
    QuestDefinition(
        id_quest="genre_sampler",
        title="Genre Sampler",
        description="Have books from 4 different genres in your library.",
        category=QuestCategory.EXPLORATION,
        target=4,
        reward_xp=60,
        stat_key="distinct_categories",
    ),
    QuestDefinition(
        id_quest="genre_globetrotter",
        title="Genre Globetrotter",
        description="Have books from 6 different genres in your library.",
        category=QuestCategory.EXPLORATION,
        target=6,
        reward_xp=90,
        stat_key="distinct_categories",
    ),
    QuestDefinition(
        id_quest="author_tour",
        title="Author Tour",
        description="Finish books by 3 different authors.",
        category=QuestCategory.EXPLORATION,
        target=3,
        reward_xp=40,
        stat_key="distinct_authors",
    ),
    QuestDefinition(
        id_quest="chorus_of_voices",
        title="A Chorus of Voices",
        description="Finish books by 8 different authors.",
        category=QuestCategory.EXPLORATION,
        target=8,
        reward_xp=90,
        stat_key="distinct_authors",
    ),
    QuestDefinition(
        id_quest="plan_next_read",
        title="Plan Your Next Read",
        description="Add 3 books to your Want to Read list.",
        category=QuestCategory.EXPLORATION,
        target=3,
        reward_xp=20,
        stat_key="want_to_read_books",
    ),
    QuestDefinition(
        id_quest="book_lover",
        title="Love at First Sight",
        description="Add a book to your favorites.",
        category=QuestCategory.ENGAGEMENT,
        target=1,
        reward_xp=20,
        stat_key="favorite_books",
    ),
    QuestDefinition(
        id_quest="top_shelf",
        title="Top Shelf",
        description="Add 5 books to your favorites.",
        category=QuestCategory.ENGAGEMENT,
        target=5,
        reward_xp=40,
        stat_key="favorite_books",
    ),
    QuestDefinition(
        id_quest="show_some_love",
        title="Show Some Love",
        description="Like 3 books.",
        category=QuestCategory.ENGAGEMENT,
        target=3,
        reward_xp=15,
        stat_key="liked_books",
    ),
    QuestDefinition(
        id_quest="start_a_playlist",
        title="Start a Playlist",
        description="Create your first playlist.",
        category=QuestCategory.ENGAGEMENT,
        target=1,
        reward_xp=20,
        stat_key="playlists_count",
    ),
    QuestDefinition(
        id_quest="playlist_architect",
        title="Playlist Architect",
        description="Create 3 playlists.",
        category=QuestCategory.ENGAGEMENT,
        target=3,
        reward_xp=45,
        stat_key="playlists_count",
    ),
    QuestDefinition(
        id_quest="fill_the_playlists",
        title="Fill the Playlists",
        description="Put 10 books in your playlists.",
        category=QuestCategory.ENGAGEMENT,
        target=10,
        reward_xp=40,
        stat_key="playlist_books",
    ),
    QuestDefinition(
        id_quest="stock_the_shelves",
        title="Stock the Shelves",
        description="Have 10 books in your library.",
        category=QuestCategory.ENGAGEMENT,
        target=10,
        reward_xp=30,
        stat_key="library_size",
    ),
    QuestDefinition(
        id_quest="growing_collection",
        title="Growing Collection",
        description="Have 25 books in your library.",
        category=QuestCategory.ENGAGEMENT,
        target=25,
        reward_xp=60,
        stat_key="library_size",
    ),
    QuestDefinition(
        id_quest="mark_the_date",
        title="Mark the Date",
        description="Record the finish date of a book you have finished.",
        category=QuestCategory.ENGAGEMENT,
        target=1,
        reward_xp=15,
        stat_key="dated_books",
    ),
    QuestDefinition(
        id_quest="reading_log",
        title="Reading Log",
        description="Record the finish date of 5 books you have finished.",
        category=QuestCategory.ENGAGEMENT,
        target=5,
        reward_xp=40,
        stat_key="dated_books",
    ),
    QuestDefinition(
        id_quest="reading_circle",
        title="Reading Circle",
        description="Follow 2 other readers.",
        category=QuestCategory.SOCIAL,
        target=2,
        reward_xp=30,
        stat_key="following_count",
    ),
    QuestDefinition(
        id_quest="make_connections",
        title="Make Connections",
        description="Follow 5 other readers.",
        category=QuestCategory.SOCIAL,
        target=5,
        reward_xp=50,
        stat_key="following_count",
    ),
    QuestDefinition(
        id_quest="gain_first_follower",
        title="Someone's Listening",
        description="Gain your first follower.",
        category=QuestCategory.SOCIAL,
        target=1,
        reward_xp=25,
        stat_key="followers_count",
    ),
    QuestDefinition(
        id_quest="fan_club",
        title="Fan Club",
        description="Gain 5 followers.",
        category=QuestCategory.SOCIAL,
        target=5,
        reward_xp=70,
        stat_key="followers_count",
    ),
    QuestDefinition(
        id_quest="find_kindred_spirit",
        title="Find a Kindred Spirit",
        description="Follow a reader who follows you back.",
        category=QuestCategory.SOCIAL,
        target=1,
        reward_xp=30,
        stat_key="mutual_follows",
    ),
    QuestDefinition(
        id_quest="share_your_thoughts",
        title="Share Your Thoughts",
        description="Write your first review.",
        category=QuestCategory.SOCIAL,
        target=1,
        reward_xp=25,
        stat_key="reviews_count",
    ),
    QuestDefinition(
        id_quest="critic_in_training",
        title="Critic in Training",
        description="Write 5 reviews.",
        category=QuestCategory.SOCIAL,
        target=5,
        reward_xp=60,
        stat_key="reviews_count",
    ),
    QuestDefinition(
        id_quest="introduce_yourself",
        title="Introduce Yourself",
        description="Complete your profile with a bio and a picture.",
        category=QuestCategory.SOCIAL,
        target=2,
        reward_xp=20,
        stat_key="profile_fields",
    ),
)


class QuestService:
    """Evaluate user quests and their completion status.

    Attributes
    ----------
    dao : QuestDAO
        Associated QuestDAO instance.

    """

    def __init__(self, quest_dao: QuestDAO) -> None:
        """Initialize QuestService with a QuestDAO.

        Parameters
        ----------
        quest_dao : QuestDAO
            DAO used to retrieve user metrics.

        """
        self.dao = quest_dao

    def get_quests(
        self,
        user_id: int,
        status_filter: Literal["all", "active", "completed"] = "all",
    ) -> list[Quest]:
        """Get the list of quests and current progress for a user.

        Parameters
        ----------
        user_id : int
            ID of the user.
        status_filter : {'all', 'active', 'completed'}, optional
            Which completion status to include. By default, include all quests.

        Returns
        -------
        list[Quest]
            List of evaluated Quest objects.

        """
        stats: QuestUserStats = self.dao.get_user_stats(user_id)
        stats_dict = stats.model_dump()

        all_quests: list[Quest] = [
            defn.evaluate(current=stats_dict.get(defn.stat_key, 0))
            for defn in QUEST_DEFINITIONS
        ]

        if status_filter == "active":
            return [q for q in all_quests if not q.is_completed]
        if status_filter == "completed":
            return [q for q in all_quests if q.is_completed]
        return all_quests
