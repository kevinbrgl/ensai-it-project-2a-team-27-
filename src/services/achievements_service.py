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
        title="Premier Ouvrage",
        description="Terminez la lecture de votre premier livre.",
        category=AchievementCategory.READING,
        tier=AchievementTier.BRONZE,
        icon="🌱",
        target=1,
        stat_key="completed_books",
    ),
    AchievementDefinition(
        id_achievement="apprentice_reader",
        title="Lecteur Assidu",
        description="Terminez la lecture d'au moins 5 livres.",
        category=AchievementCategory.READING,
        tier=AchievementTier.SILVER,
        icon="📖",
        target=5,
        stat_key="completed_books",
    ),
    AchievementDefinition(
        id_achievement="bibliophile",
        title="Bibliophile Émérite",
        description="Terminez la lecture d'au moins 15 livres.",
        category=AchievementCategory.READING,
        tier=AchievementTier.GOLD,
        icon="📚",
        target=15,
        stat_key="completed_books",
    ),
    AchievementDefinition(
        id_achievement="page_turner",
        title="Cap des 1 000 Pages",
        description="Lisez un total cumulé d'au moins 1 000 pages.",
        category=AchievementCategory.READING,
        tier=AchievementTier.SILVER,
        icon="📜",
        target=1000,
        stat_key="pages_read",
    ),
    AchievementDefinition(
        id_achievement="century_reader",
        title="Marathonien du Livre",
        description="Lisez un total cumulé d'au moins 5 000 pages.",
        category=AchievementCategory.READING,
        tier=AchievementTier.PLATINUM,
        icon="👑",
        target=5000,
        stat_key="pages_read",
    ),
    AchievementDefinition(
        id_achievement="genre_curious",
        title="Esprit Éclectique",
        description="Lisez des livres appartenant à au moins 3 genres.",
        category=AchievementCategory.EXPLORATION,
        tier=AchievementTier.BRONZE,
        icon="🧭",
        target=3,
        stat_key="distinct_genres",
    ),
    AchievementDefinition(
        id_achievement="literary_polymath",
        title="Polymathe Littéraire",
        description="Lisez des livres appartenant à au moins 7 genres.",
        category=AchievementCategory.EXPLORATION,
        tier=AchievementTier.GOLD,
        icon="🌍",
        target=7,
        stat_key="distinct_genres",
    ),
    AchievementDefinition(
        id_achievement="first_review",
        title="Première Impression",
        description="Rédigez et publiez votre premier avis littéraire.",
        category=AchievementCategory.COMMUNITY,
        tier=AchievementTier.BRONZE,
        icon="✍️",
        target=1,
        stat_key="reviews_count",
    ),
    AchievementDefinition(
        id_achievement="literary_critic",
        title="Critique Reconnu",
        description="Rédigez au moins 5 avis littéraires détaillés.",
        category=AchievementCategory.COMMUNITY,
        tier=AchievementTier.SILVER,
        icon="🖋️",
        target=5,
        stat_key="reviews_count",
    ),
    AchievementDefinition(
        id_achievement="social_circle",
        title="Cercle Littéraire",
        description="Suivez au moins 3 autres lecteurs de la communauté.",
        category=AchievementCategory.SOCIAL,
        tier=AchievementTier.BRONZE,
        icon="🤝",
        target=3,
        stat_key="following_count",
    ),
    AchievementDefinition(
        id_achievement="curator",
        title="Conservateur Littéraire",
        description="Créez au moins 2 playlists thématiques.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.BRONZE,
        icon="📁",
        target=2,
        stat_key="playlists_count",
    ),
    AchievementDefinition(
        id_achievement="treasured_shelf",
        title="Étagère Dorée",
        description="Ajoutez au moins 3 livres à vos coups de cœur.",
        category=AchievementCategory.COLLECTION,
        tier=AchievementTier.BRONZE,
        icon="❤️",
        target=3,
        stat_key="favorites_count",
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
