"""Service layer for quest management and progress evaluation.

Computes active quests and user progress based on DAO stats.
"""

from dataclasses import dataclass
from typing import Literal

from src.dao.quests_dao import QuestDAO
from src.models.quests import Quest, QuestCategory, QuestUserStats


@dataclass(frozen=True)
class QuestDefinition:
    """Static definition of a quest in Ex-Libris."""

    id_quest: str
    title: str
    description: str
    category: QuestCategory
    target: int
    reward_xp: int
    stat_key: str

    def evaluate(self, current: int) -> Quest:
        """Evaluate quest progress against a current metric value.

        :param current: Current value achieved by the user
        :return: Evaluated Quest schema instance
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
        title="Premier pas littéraire",
        description="Terminez la lecture d'au moins 1 livre.",
        category=QuestCategory.READING,
        target=1,
        reward_xp=25,
        stat_key="completed_books",
    ),
    QuestDefinition(
        id_quest="reading_marathon",
        title="Dévoreur de pages",
        description="Terminez la lecture d'au moins 3 livres.",
        category=QuestCategory.READING,
        target=3,
        reward_xp=50,
        stat_key="completed_books",
    ),
    QuestDefinition(
        id_quest="currently_reading",
        title="Dans le vif du sujet",
        description="Ayez au moins 1 livre en cours de lecture.",
        category=QuestCategory.READING,
        target=1,
        reward_xp=15,
        stat_key="reading_books",
    ),
    QuestDefinition(
        id_quest="genre_explorer",
        title="Explorateur de genres",
        description=(
            "Ajoutez des livres d'au moins 2 genres différents "
            "dans votre bibliothèque."
        ),
        category=QuestCategory.EXPLORATION,
        target=2,
        reward_xp=40,
        stat_key="distinct_categories",
    ),
    QuestDefinition(
        id_quest="book_lover",
        title="Coup de cœur",
        description="Ajoutez au moins 1 livre à vos favoris.",
        category=QuestCategory.ENGAGEMENT,
        target=1,
        reward_xp=20,
        stat_key="favorite_books",
    ),
    QuestDefinition(
        id_quest="cercle_litteraire",
        title="Cercle littéraire",
        description="Suivez au moins 2 autres lecteurs passionnés.",
        category=QuestCategory.SOCIAL,
        target=2,
        reward_xp=30,
        stat_key="following_count",
    ),
)


class QuestService:
    """Service class for evaluating user quests.

    :attr dao: Associated QuestDAO instance
    """

    def __init__(self, quest_dao: QuestDAO) -> None:
        """Initialize QuestService with a QuestDAO.

        :param quest_dao: DAO used to retrieve user metrics
        """
        self.dao = quest_dao

    def get_quests(
        self,
        user_id: int,
        status_filter: Literal["all", "active", "completed"] = "all",
    ) -> list[Quest]:
        """Get the list of quests and current progress for a user.

        :param user_id: ID of the user
        :param status_filter: Filter by 'all', 'active' (not completed),
            or 'completed'
        :return: List of evaluated Quest objects
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
