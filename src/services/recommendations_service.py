"""Service layer for book recommendations."""

import logging
from collections import Counter
from datetime import date
from typing import TYPE_CHECKING

from src.dao.recommendations_dao import RecommendationDAO
from src.dao.stats_dao import StatsDAO
from src.models.recommendations import Recommendation, RecommendationSort
from src.services.books_service import BookService
from src.utils.exceptions import ExternalServiceError

if TYPE_CHECKING:
    from src.models.books import Book
    from src.models.stats import GenreCount

logger = logging.getLogger(__name__)

MAX_FAVORITE_GENRES = 3
MIN_LIKED_RATING = 4
CANDIDATE_FACTOR = 2
MAX_CANDIDATES_PER_GENRE = 50
HISTORY_REASON = "Because you like {genre}"
REQUESTED_REASON = "Popular in {genre}"
TOP_RATED_REASON = "Top rated"


class RecommendationService:
    """Find book recommendations for users."""

    def __init__(
        self,
        recommendation_dao: RecommendationDAO,
        stats_dao: StatsDAO,
        book_service: BookService,
    ) -> None:
        """Initialize the service with its dependencies.

        Parameters
        ----------
        recommendation_dao : RecommendationDAO
            The recommendation data access object.
        stats_dao : StatsDAO
            The statistics data access object.
        book_service : BookService
            The book service (Open Library + book upsert).

        """
        self.recommendation_dao = recommendation_dao
        self.stats_dao = stats_dao
        self.book_service = book_service

    def get_recommendations(
        self,
        id_user: int,
        genre: str | None = None,
        sort: RecommendationSort = "rating",
        limit: int = 10,
    ) -> list[Recommendation]:
        """Recommend books to a user.

        Search Open Library using the requested genre or the user's reading
        history. Use locally reviewed books when the user has no reading
        history, Open Library fails, or the search yields no eligible books.

        Parameters
        ----------
        id_user : int
            ID of the user.
        genre : str | None, optional
            Genre requested by the user.
        sort : RecommendationSort, optional
            Sort order of the recommendations.
        limit : int, optional
            Maximum number of recommendations.

        Returns
        -------
        list[Recommendation]
            Up to the requested number of recommendations in the chosen order.

        """
        clean_genre = genre.strip() if genre and genre.strip() else None

        if clean_genre:
            genres = [clean_genre]
            reason_template = REQUESTED_REASON
        else:
            genres = self._favorite_genres(id_user)
            reason_template = HISTORY_REASON

        recommendations = (
            self._from_open_library(
                id_user,
                genres,
                reason_template,
                sort,
                limit,
            )
            if genres
            else []
        )
        if recommendations:
            return recommendations

        return self._fallback(id_user, clean_genre, sort, limit)

    def _favorite_genres(self, id_user: int) -> list[str]:
        """Find the favorite genres of a user.

        Count genres across the user's library and count books rated at least
        four a second time.

        Parameters
        ----------
        id_user : int
            ID of the user.

        Returns
        -------
        list[str]
            Up to three genres, most frequent first.

        """
        counts: Counter[str] = Counter()
        sources: list[list[GenreCount]] = [
            self.stats_dao.count_genres(id_user),
            self.recommendation_dao.count_rated_genres(
                id_user,
                MIN_LIKED_RATING,
            ),
        ]
        for genre_counts in sources:
            for genre_count in genre_counts:
                if genre_count.category and genre_count.category.strip():
                    counts[genre_count.category.strip()] += genre_count.count

        return [genre for genre, _ in counts.most_common(MAX_FAVORITE_GENRES)]

    def _from_open_library(
        self,
        id_user: int,
        genres: list[str],
        reason_template: str,
        sort: RecommendationSort,
        limit: int,
    ) -> list[Recommendation]:
        """Build recommendations from Open Library subject searches.

        Exclude books already in the user's library and deduplicate candidates
        by Open Library key. Use local average ratings when available.

        Parameters
        ----------
        id_user : int
            ID of the user.
        genres : list[str]
            Genres to search for.
        reason_template : str
            Explanation template with a {genre} placeholder.
        sort : RecommendationSort
            Sort order of the recommendations.
        limit : int
            Maximum number of recommendations.

        Returns
        -------
        list[Recommendation]
            The recommendations, or an empty list.

        """
        excluded_keys = self.recommendation_dao.find_library_api_keys(
            id_user,
        )
        per_genre = min(limit * CANDIDATE_FACTOR, MAX_CANDIDATES_PER_GENRE)

        seen_keys: set[str] = set()
        candidates: list[tuple[Book, float | None, str]] = []
        for genre in genres:
            try:
                results = self.book_service.search_by_subject(
                    genre,
                    limit=per_genre,
                    sort="rating",
                )
            except ExternalServiceError:
                logger.warning(
                    "Open Library unavailable for genre %s",
                    genre,
                )
                continue

            for book_create, open_library_rating in results:
                key = book_create.id_book_api
                if not key or key in excluded_keys or key in seen_keys:
                    continue
                seen_keys.add(key)
                book = self.book_service.save_book(book_create)
                candidates.append(
                    (
                        book,
                        open_library_rating,
                        reason_template.format(genre=genre),
                    ),
                )

        if not candidates:
            return []

        local_ratings = self.recommendation_dao.get_average_ratings(
            [book.id_book for book, _, _ in candidates],
        )
        recommendations = [
            Recommendation(
                book=book,
                score=local_ratings.get(book.id_book, open_library_rating),
                reason=reason,
            )
            for book, open_library_rating, reason in candidates
        ]
        return self._sort(recommendations, sort)[:limit]

    def _fallback(
        self,
        id_user: int,
        genre: str | None,
        sort: RecommendationSort,
        limit: int,
    ) -> list[Recommendation]:
        """Recommend books with the highest local review ratings.

        Parameters
        ----------
        id_user : int
            ID of the user whose library is excluded.
        genre : str | None
            Optional genre filter.
        sort : RecommendationSort
            Sort order of the recommendations.
        limit : int
            Maximum number of recommendations.

        Returns
        -------
        list[Recommendation]
            The recommendations.

        """
        rows = self.recommendation_dao.find_top_rated_books(
            id_user,
            limit,
            genre,
        )
        reason = (
            f"{TOP_RATED_REASON} in {genre}" if genre else TOP_RATED_REASON
        )
        recommendations = [
            Recommendation(book=book, score=average, reason=reason)
            for book, average in rows
        ]
        return self._sort(recommendations, sort)

    @staticmethod
    def _sort(
        recommendations: list[Recommendation],
        sort: RecommendationSort,
    ) -> list[Recommendation]:
        """Order recommendations by rating, publication date, or title.

        Parameters
        ----------
        recommendations : list[Recommendation]
            Recommendations to sort.
        sort : RecommendationSort
            Choose "rating" for highest first, "new" for newest first, or
            "title" for alphabetical order.

        Returns
        -------
        list[Recommendation]
            The sorted recommendations.

        """
        if sort == "title":
            return sorted(
                recommendations,
                key=lambda rec: rec.book.title.casefold(),
            )
        if sort == "new":
            return sorted(
                recommendations,
                key=lambda rec: rec.book.publish_date or date.min,
                reverse=True,
            )
        return sorted(
            recommendations,
            key=lambda rec: (
                rec.score if rec.score is not None else float("-inf")
            ),
            reverse=True,
        )
