"""Service layer for reading statistics."""

from src.dao.stats_dao import StatsDAO
from src.models.stats import RatingCount, UserStats

RATINGS = range(1, 6)


class StatsService:
    """Service class building a user's reading statistics."""

    def __init__(self, dao: StatsDAO) -> None:
        """Initialize the service with a DAO.

        :param dao: The statistics data access object
        """
        self.dao = dao

    def get_stats(self, id_user: int) -> UserStats:
        """Build the reading statistics of a user.

        Every rating from 1 to 5 is listed, with a count of 0 when unused.

        :param id_user: ID of the user
        :return: The user's statistics
        """
        ratings = self.dao.count_ratings(id_user)
        return UserStats(
            books_finished=self.dao.count_finished_books(id_user),
            genres=self.dao.count_genres(id_user),
            ratings=[
                RatingCount(rating=rating, count=ratings.get(rating, 0))
                for rating in RATINGS
            ],
        )
