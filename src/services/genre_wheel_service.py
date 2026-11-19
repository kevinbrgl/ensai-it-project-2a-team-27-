"""Service layer for computing user avatar genre color wheels.

Calculates weighted genre proportions based on reading volume,
user review ratings, and favorite markers.
"""

import hashlib
import math
from collections import defaultdict
from operator import itemgetter
from typing import Any

from src.dao.genre_wheel_dao import GenreWheelDAO
from src.models.genre_wheel import GenreWheel, GenreWheelSegment

MIN_GENRE_SHARE = 3.0
MAX_GENRE_SEGMENTS = 7
DEFAULT_EMPTY_COLOR = "#9CA3AF"

BASE_RATING_WEIGHTS: dict[int, float] = {
    1: 0.1,
    2: 0.4,
    3: 1.0,
    4: 2.0,
    5: 3.5,
}
DEFAULT_UNRATED_WEIGHT = 1.0
FAVORITE_BONUS_WEIGHT = 1.5

GENRE_COLORS: dict[str, str] = {
    "romance": "#F43F5E",
    "science-fiction": "#8B5CF6",
    "sci-fi": "#8B5CF6",
    "science fiction": "#8B5CF6",
    "fantasy": "#EC4899",
    "fantastique": "#D946EF",
    "thriller": "#EAB308",
    "policier": "#F59E0B",
    "mystery": "#EAB308",
    "horror": "#DC2626",
    "horreur": "#DC2626",
    "fiction": "#3B82F6",
    "history": "#B45309",
    "histoire": "#B45309",
    "biography": "#10B981",
    "biographie": "#10B981",
    "autobiography": "#10B981",
    "manga": "#F97316",
    "comics": "#FB923C",
    "bande dessinée": "#FB923C",
    "poetry": "#A855F7",
    "poésie": "#A855F7",
    "philosophy": "#06B6D4",
    "philosophie": "#06B6D4",
    "adventure": "#0EA5E9",
    "aventure": "#0EA5E9",
    "non-fiction": "#14B8A6",
    "young adult": "#06D6A0",
    "jeunesse": "#10B981",
    "classics": "#64748B",
    "classique": "#64748B",
}

DEFAULT_PALETTE: tuple[str, ...] = (
    "#3B82F6",  # Blue
    "#8B5CF6",  # Purple
    "#EC4899",  # Pink
    "#F43F5E",  # Rose
    "#F97316",  # Orange
    "#EAB308",  # Amber
    "#10B981",  # Emerald
    "#06B6D4",  # Cyan
    "#6366F1",  # Indigo
    "#14B8A6",  # Teal
    "#F472B6",  # Light Pink
    "#A855F7",  # Violet
)


class GenreWheelService:
    """Compute genre proportions and colors for user profiles.

    Attributes
    ----------
    dao : GenreWheelDAO
        Associated GenreWheelDAO instance.

    """

    def __init__(self, dao: GenreWheelDAO) -> None:
        """Initialize GenreWheelService with a GenreWheelDAO.

        Parameters
        ----------
        dao : GenreWheelDAO
            DAO used to retrieve user activities and ratings.

        """
        self.dao = dao

    @staticmethod
    def resolve_color(genre: str) -> str:
        """Resolve a consistent hex color for a book genre.

        Known genres use fixed colors. Other names map to a palette color based
        on their normalized spelling.

        Parameters
        ----------
        genre : str
            Genre name string.

        Returns
        -------
        str
            Hex color code (e.g. #F43F5E).

        """
        normalized = genre.strip().lower()
        if normalized in GENRE_COLORS:
            return GENRE_COLORS[normalized]

        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        palette_idx = int(digest, 16) % len(DEFAULT_PALETTE)
        return DEFAULT_PALETTE[palette_idx]

    @staticmethod
    def _compute_book_weight(
        rating: int | None,
        *,
        is_favorite: bool,
    ) -> float:
        """Calculate the individual weight score of a finished book.

        The review rating sets the base weight. A favorite book receives a
        fixed bonus.

        Parameters
        ----------
        rating : int | None
            User review rating between 1 and 5 (or None).
        is_favorite : bool
            Whether marked as favorite.

        Returns
        -------
        float
            Computed weight score.

        """
        base = (
            BASE_RATING_WEIGHTS.get(rating, DEFAULT_UNRATED_WEIGHT)
            if rating is not None
            else DEFAULT_UNRATED_WEIGHT
        )
        if is_favorite:
            base += FAVORITE_BONUS_WEIGHT
        return base

    def _aggregate_books(
        self,
        books: list[dict[str, Any]],
    ) -> tuple[dict[str, float], dict[str, int], dict[str, list[int]]]:
        """Aggregate scores, counts, and ratings per book category.

        Parameters
        ----------
        books : list[dict[str, Any]]
            Finished-book records with category, review rating and favorite
            status.

        Returns
        -------
        scores : dict[str, float]
            Total weight per category.
        counts : dict[str, int]
            Finished-book count per category.
        ratings : dict[str, list[int]]
            Integer review ratings per category.

        """
        scores: dict[str, float] = defaultdict(float)
        counts: dict[str, int] = defaultdict(int)
        ratings: dict[str, list[int]] = defaultdict(list)

        for b in books:
            cat = str(b.get("category", "")).strip()
            if not cat:
                continue

            rating = b.get("rating")
            is_fav = bool(b.get("is_favorite"))
            weight = self._compute_book_weight(
                rating,
                is_favorite=is_fav,
            )

            scores[cat] += weight
            counts[cat] += 1
            if rating is not None and isinstance(rating, int):
                ratings[cat].append(rating)

        return scores, counts, ratings

    def _build_segments(
        self,
        scores: dict[str, float],
        counts: dict[str, int],
        ratings: dict[str, list[int]],
    ) -> list[GenreWheelSegment]:
        """Select genre segments and normalize their shares.

        Keep up to the configured maximum number of genres in descending weight
        order and normalize their shares to 100 percent.

        Parameters
        ----------
        scores : dict[str, float]
            Total score per genre.
        counts : dict[str, int]
            Total book count per genre.
        ratings : dict[str, list[int]]
            Collected ratings per genre.

        Returns
        -------
        list[GenreWheelSegment]
            Genre segments in descending weight order, or an empty list when
            the total weight is zero.

        """
        total_weight = sum(scores.values())
        if total_weight <= 0.0 or not scores:
            return []

        preliminary: list[dict[str, Any]] = [
            {
                "genre": cat,
                "raw_score": score,
                "book_count": counts[cat],
                "ratings": ratings[cat],
                "share": (score / total_weight) * 100.0,
            }
            for cat, score in scores.items()
        ]

        preliminary.sort(key=itemgetter("raw_score"), reverse=True)

        significant = [
            item for item in preliminary if item["share"] >= MIN_GENRE_SHARE
        ]
        if not significant:
            significant = preliminary[:MAX_GENRE_SEGMENTS]
        else:
            significant = significant[:MAX_GENRE_SEGMENTS]

        remaining_weight = sum(item["raw_score"] for item in significant)
        segments: list[GenreWheelSegment] = []

        for item in significant:
            pct = round((item["raw_score"] / remaining_weight) * 100.0, 1)
            ratings_list = item["ratings"]
            avg_rating = (
                round(sum(ratings_list) / len(ratings_list), 1)
                if ratings_list
                else None
            )
            segments.append(
                GenreWheelSegment(
                    genre=item["genre"],
                    color=self.resolve_color(item["genre"]),
                    percentage=pct,
                    book_count=item["book_count"],
                    average_rating=avg_rating,
                    raw_score=round(item["raw_score"], 2),
                ),
            )

        if segments:
            diff = round(100.0 - sum(s.percentage for s in segments), 1)
            if not math.isclose(diff, 0.0, abs_tol=1e-4):
                segments[0].percentage = round(
                    segments[0].percentage + diff,
                    1,
                )

        return segments

    def get_genre_wheel(self, user_id: int) -> GenreWheel:
        """Build the avatar genre color wheel for a given user.

        Parameters
        ----------
        user_id : int
            ID of the user whose wheel is built.

        Returns
        -------
        GenreWheel
            GenreWheel model containing segments or empty state.

        """
        books: list[dict[str, Any]] = self.dao.get_user_completed_books(
            user_id,
        )
        if not books:
            return GenreWheel(
                id_user=user_id,
                is_empty=True,
                empty_color=DEFAULT_EMPTY_COLOR,
                total_books=0,
                segments=[],
            )

        scores, counts, ratings = self._aggregate_books(books)
        segments = self._build_segments(scores, counts, ratings)

        is_empty = len(segments) == 0
        return GenreWheel(
            id_user=user_id,
            is_empty=is_empty,
            empty_color=DEFAULT_EMPTY_COLOR,
            total_books=len(books),
            segments=segments,
        )
