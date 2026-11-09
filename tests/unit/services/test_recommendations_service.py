"""Unit tests for RecommendationService.

The DAOs and the BookService are mocked: no database or network is needed.
"""

from datetime import date
from itertools import count
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from src.dao.recommendations_dao import RecommendationDAO
from src.dao.stats_dao import StatsDAO
from src.models.books import Book, BookCreate
from src.models.recommendations import Recommendation
from src.models.stats import GenreCount
from src.services.books_service import BookService
from src.services.recommendations_service import RecommendationService
from src.utils.exceptions import ExternalServiceError

ID_USER = 1


def candidate(
    key: str | None,
    title: str = "Book",
    rating: float | None = None,
    publish_date: date | None = None,
) -> tuple[BookCreate, float | None]:
    """Build an Open Library candidate as returned by search_by_subject."""
    return (
        BookCreate(id_book_api=key, title=title, publish_date=publish_date),
        rating,
    )


def make_book(
    id_book: int,
    title: str = "Book",
    publish_date: date | None = None,
) -> Book:
    """Build a Book stored in the database."""
    return Book(
        id_book=id_book,
        id_book_api=f"/works/OL{id_book}W",
        title=title,
        publish_date=publish_date,
    )


@pytest.fixture
def rec_dao(mocker: MockerFixture) -> Mock:
    """Return a fake RecommendationDAO."""
    dao = mocker.Mock(spec=RecommendationDAO)
    dao.count_rated_genres.return_value = []
    dao.find_library_api_keys.return_value = set()
    dao.get_average_ratings.return_value = {}
    dao.find_top_rated_books.return_value = []
    return dao


@pytest.fixture
def stats_dao(mocker: MockerFixture) -> Mock:
    """Return a fake StatsDAO."""
    dao = mocker.Mock(spec=StatsDAO)
    dao.count_genres.return_value = []
    return dao


@pytest.fixture
def book_service(mocker: MockerFixture) -> Mock:
    """Return a fake BookService whose save_book gives increasing IDs."""
    service = mocker.Mock(spec=BookService)
    service.search_by_subject.return_value = []
    ids = count(1)

    def save(book_create: BookCreate) -> Book:
        return Book(id_book=next(ids), **book_create.model_dump())

    service.save_book.side_effect = save
    return service


@pytest.fixture
def service(
    rec_dao: Mock,
    stats_dao: Mock,
    book_service: Mock,
) -> RecommendationService:
    """Return a RecommendationService using the mocks."""
    return RecommendationService(rec_dao, stats_dao, book_service)


def searched_genres(book_service: Mock) -> list[str]:
    """Return the genres passed to search_by_subject, in order."""
    return [c.args[0] for c in book_service.search_by_subject.call_args_list]


class TestFavoriteGenres:
    """Tests for the selection of the user's favorite genres."""

    def test_merges_library_and_rated_genres_top_three(
        self,
        service: RecommendationService,
        rec_dao: Mock,
        stats_dao: Mock,
        book_service: Mock,
    ) -> None:
        """Library and rated genres are added up, the 3 best are kept."""
        stats_dao.count_genres.return_value = [
            GenreCount(category="Fantasy", count=2),
            GenreCount(category="Romance", count=1),
        ]
        rec_dao.count_rated_genres.return_value = [
            GenreCount(category="Sci-Fi", count=3),
            GenreCount(category="Horror", count=1),
        ]

        service.get_recommendations(ID_USER)

        assert searched_genres(book_service) == [
            "Sci-Fi",
            "Fantasy",
            "Romance",
        ]

    def test_same_genre_in_both_sources_is_summed(
        self,
        service: RecommendationService,
        rec_dao: Mock,
        stats_dao: Mock,
        book_service: Mock,
    ) -> None:
        """A genre in the library and in the ratings counts for both."""
        stats_dao.count_genres.return_value = [
            GenreCount(category="Fantasy", count=1),
            GenreCount(category="Sci-Fi", count=2),
        ]
        rec_dao.count_rated_genres.return_value = [
            GenreCount(category="Fantasy", count=2),
        ]

        service.get_recommendations(ID_USER)

        assert searched_genres(book_service) == ["Fantasy", "Sci-Fi"]

    def test_ignores_empty_categories(
        self,
        service: RecommendationService,
        stats_dao: Mock,
        book_service: Mock,
    ) -> None:
        """None and blank categories are not genres."""
        stats_dao.count_genres.return_value = [
            GenreCount(category=None, count=5),
            GenreCount(category="   ", count=3),
            GenreCount(category="Fantasy", count=1),
        ]

        service.get_recommendations(ID_USER)

        assert searched_genres(book_service) == ["Fantasy"]

    def test_strips_categories(
        self,
        service: RecommendationService,
        rec_dao: Mock,
        stats_dao: Mock,
        book_service: Mock,
    ) -> None:
        """Categories differing only by spaces are merged."""
        stats_dao.count_genres.return_value = [
            GenreCount(category=" Fantasy ", count=1),
        ]
        rec_dao.count_rated_genres.return_value = [
            GenreCount(category="Fantasy", count=1),
        ]

        service.get_recommendations(ID_USER)

        assert searched_genres(book_service) == ["Fantasy"]

    def test_daos_called_for_the_user(
        self,
        service: RecommendationService,
        rec_dao: Mock,
        stats_dao: Mock,
    ) -> None:
        """History is read for the user, with books rated 4 or more."""
        service.get_recommendations(ID_USER)

        stats_dao.count_genres.assert_called_once_with(ID_USER)
        rec_dao.count_rated_genres.assert_called_once_with(ID_USER, 4)


class TestRequestedGenre:
    """Tests for the genre query parameter."""

    def test_uses_requested_genre_only(
        self,
        service: RecommendationService,
        stats_dao: Mock,
        book_service: Mock,
    ) -> None:
        """A requested genre replaces the history."""
        book_service.search_by_subject.return_value = [candidate("/works/A")]

        result = service.get_recommendations(ID_USER, genre="Fantasy")

        stats_dao.count_genres.assert_not_called()
        book_service.search_by_subject.assert_called_once_with(
            "Fantasy",
            limit=20,
            sort="rating",
        )
        assert [r.reason for r in result] == ["Popular in Fantasy"]

    def test_requested_genre_is_stripped(
        self,
        service: RecommendationService,
        book_service: Mock,
    ) -> None:
        """Spaces around the requested genre are removed."""
        service.get_recommendations(ID_USER, genre="  Fantasy  ")

        assert searched_genres(book_service) == ["Fantasy"]

    def test_blank_genre_uses_history(
        self,
        service: RecommendationService,
        stats_dao: Mock,
    ) -> None:
        """A blank genre is treated as no genre."""
        service.get_recommendations(ID_USER, genre="   ")

        stats_dao.count_genres.assert_called_once_with(ID_USER)


@pytest.mark.usefixtures("history")
class TestOpenLibraryCandidates:
    """Tests for the recommendations built from Open Library."""

    @pytest.fixture
    def history(self, stats_dao: Mock) -> None:
        """Give the user a Fantasy history."""
        stats_dao.count_genres.return_value = [
            GenreCount(category="Fantasy", count=1),
        ]

    def test_reason_mentions_favorite_genre(
        self,
        service: RecommendationService,
        book_service: Mock,
    ) -> None:
        """History recommendations explain the genre."""
        book_service.search_by_subject.return_value = [candidate("/works/A")]

        result = service.get_recommendations(ID_USER)

        assert [r.reason for r in result] == ["Because you like Fantasy"]

    def test_excludes_library_books(
        self,
        service: RecommendationService,
        rec_dao: Mock,
        book_service: Mock,
    ) -> None:
        """Books whose key is in the library are not recommended."""
        rec_dao.find_library_api_keys.return_value = {"/works/OWNED"}
        book_service.search_by_subject.return_value = [
            candidate("/works/OWNED", "Owned"),
            candidate("/works/NEW", "New"),
        ]

        result = service.get_recommendations(ID_USER)

        assert [r.book.title for r in result] == ["New"]
        book_service.save_book.assert_called_once()
        rec_dao.find_library_api_keys.assert_called_once_with(ID_USER)

    def test_skips_candidates_without_key(
        self,
        service: RecommendationService,
        book_service: Mock,
    ) -> None:
        """Candidates without an Open Library key are skipped."""
        book_service.search_by_subject.return_value = [
            candidate(None, "No key"),
            candidate("/works/A", "With key"),
        ]

        result = service.get_recommendations(ID_USER)

        assert [r.book.title for r in result] == ["With key"]

    def test_deduplicates_across_genres(
        self,
        service: RecommendationService,
        stats_dao: Mock,
        book_service: Mock,
    ) -> None:
        """A book found for two genres is kept once, with the first reason."""
        stats_dao.count_genres.return_value = [
            GenreCount(category="Fantasy", count=2),
            GenreCount(category="Adventure", count=1),
        ]
        book_service.search_by_subject.side_effect = [
            [candidate("/works/A", "Shared")],
            [candidate("/works/A", "Shared"), candidate("/works/B", "Other")],
        ]

        result = service.get_recommendations(ID_USER, sort="title")

        assert [(r.book.title, r.reason) for r in result] == [
            ("Other", "Because you like Adventure"),
            ("Shared", "Because you like Fantasy"),
        ]
        assert book_service.save_book.call_count == len(result)

    def test_deduplicates_within_a_genre(
        self,
        service: RecommendationService,
        book_service: Mock,
    ) -> None:
        """The same key twice in one response is kept once."""
        book_service.search_by_subject.return_value = [
            candidate("/works/A"),
            candidate("/works/A"),
        ]

        result = service.get_recommendations(ID_USER)

        assert len(result) == 1

    def test_every_recommendation_has_an_id(
        self,
        service: RecommendationService,
        book_service: Mock,
    ) -> None:
        """Candidates are saved, so they all have an id_book."""
        book_service.search_by_subject.return_value = [
            candidate("/works/A"),
            candidate("/works/B"),
        ]

        result = service.get_recommendations(ID_USER)

        assert all(r.book.id_book for r in result)

    def test_local_rating_wins_over_open_library(
        self,
        service: RecommendationService,
        rec_dao: Mock,
        book_service: Mock,
    ) -> None:
        """Score = local average if known, else Open Library rating."""
        book_service.search_by_subject.return_value = [
            candidate("/works/A", "Local", rating=4.9),
            candidate("/works/B", "Open Library", rating=3.5),
            candidate("/works/C", "Unrated", rating=None),
        ]
        rec_dao.get_average_ratings.return_value = {1: 2.0}

        result = service.get_recommendations(ID_USER, sort="title")

        assert [(r.book.title, r.score) for r in result] == [
            ("Local", 2.0),
            ("Open Library", 3.5),
            ("Unrated", None),
        ]
        rec_dao.get_average_ratings.assert_called_once_with([1, 2, 3])

    def test_fetch_size_is_twice_the_limit(
        self,
        service: RecommendationService,
        book_service: Mock,
    ) -> None:
        """Open Library is asked for twice the limit."""
        service.get_recommendations(ID_USER, limit=7)

        book_service.search_by_subject.assert_called_once_with(
            "Fantasy",
            limit=14,
            sort="rating",
        )

    def test_fetch_size_is_capped(
        self,
        service: RecommendationService,
        book_service: Mock,
    ) -> None:
        """Open Library is never asked for more than 50 books."""
        service.get_recommendations(ID_USER, limit=40)

        book_service.search_by_subject.assert_called_once_with(
            "Fantasy",
            limit=50,
            sort="rating",
        )

    def test_open_library_always_sorted_by_rating(
        self,
        service: RecommendationService,
        book_service: Mock,
    ) -> None:
        """The sort parameter does not change the Open Library query."""
        service.get_recommendations(ID_USER, sort="title")

        assert book_service.search_by_subject.call_args.kwargs["sort"] == (
            "rating"
        )

    def test_truncates_to_limit(
        self,
        service: RecommendationService,
        book_service: Mock,
    ) -> None:
        """Only the first limit books are returned, best first."""
        book_service.search_by_subject.return_value = [
            candidate("/works/A", "A", rating=3.0),
            candidate("/works/B", "B", rating=5.0),
            candidate("/works/C", "C", rating=4.0),
        ]

        result = service.get_recommendations(ID_USER, limit=2)

        assert [r.book.title for r in result] == ["B", "C"]

    def test_one_genre_down_other_genre_used(
        self,
        service: RecommendationService,
        rec_dao: Mock,
        stats_dao: Mock,
        book_service: Mock,
    ) -> None:
        """If one genre fails, the other genres are still used."""
        stats_dao.count_genres.return_value = [
            GenreCount(category="Fantasy", count=2),
            GenreCount(category="Sci-Fi", count=1),
        ]
        book_service.search_by_subject.side_effect = [
            ExternalServiceError(),
            [candidate("/works/A", "Dune")],
        ]

        result = service.get_recommendations(ID_USER)

        assert [r.reason for r in result] == ["Because you like Sci-Fi"]
        rec_dao.find_top_rated_books.assert_not_called()


@pytest.mark.usefixtures("candidates")
class TestSorting:
    """Tests for the sort parameter."""

    @pytest.fixture
    def candidates(self, book_service: Mock) -> None:
        """Return three candidates for the requested genre."""
        book_service.search_by_subject.return_value = [
            candidate("/works/A", "beta", 4.0, date(2001, 1, 1)),
            candidate("/works/B", "Alpha", None, None),
            candidate("/works/C", "Gamma", 4.5, date(1990, 1, 1)),
        ]

    def test_rating_best_first_unrated_last(
        self,
        service: RecommendationService,
    ) -> None:
        """Sort by rating: highest score first, None last."""
        result = service.get_recommendations(ID_USER, genre="X")

        assert [r.book.title for r in result] == ["Gamma", "beta", "Alpha"]

    def test_title_alphabetical_case_insensitive(
        self,
        service: RecommendationService,
    ) -> None:
        """Sort by title ignores case."""
        result = service.get_recommendations(
            ID_USER,
            genre="X",
            sort="title",
        )

        assert [r.book.title for r in result] == ["Alpha", "beta", "Gamma"]

    def test_new_newest_first_undated_last(
        self,
        service: RecommendationService,
    ) -> None:
        """Sort by date: newest first, books without date last."""
        result = service.get_recommendations(ID_USER, genre="X", sort="new")

        assert [r.book.title for r in result] == ["beta", "Gamma", "Alpha"]


class TestFallback:
    """Tests for the fallback on our own reviews."""

    def test_no_history_uses_top_rated(
        self,
        service: RecommendationService,
        rec_dao: Mock,
        book_service: Mock,
    ) -> None:
        """Without history and genre, Open Library is not called."""
        rec_dao.find_top_rated_books.return_value = [
            (make_book(3, "Classic"), 4.8),
        ]

        result = service.get_recommendations(ID_USER)

        book_service.search_by_subject.assert_not_called()
        rec_dao.find_top_rated_books.assert_called_once_with(
            ID_USER,
            10,
            None,
        )
        assert [(r.book.title, r.score, r.reason) for r in result] == [
            ("Classic", 4.8, "Top rated"),
        ]

    def test_open_library_down_uses_top_rated_in_genre(
        self,
        service: RecommendationService,
        rec_dao: Mock,
        book_service: Mock,
    ) -> None:
        """If Open Library fails, local books of the genre are used."""
        book_service.search_by_subject.side_effect = ExternalServiceError()
        rec_dao.find_top_rated_books.return_value = [
            (make_book(3, "Classic"), 4.8),
        ]

        result = service.get_recommendations(
            ID_USER,
            genre="Fantasy",
            limit=5,
        )

        rec_dao.find_top_rated_books.assert_called_once_with(
            ID_USER,
            5,
            "Fantasy",
        )
        assert [r.reason for r in result] == ["Top rated in Fantasy"]

    def test_all_candidates_excluded_uses_fallback(
        self,
        service: RecommendationService,
        rec_dao: Mock,
        book_service: Mock,
    ) -> None:
        """If every candidate is in the library, the fallback is used."""
        rec_dao.find_library_api_keys.return_value = {"/works/A"}
        book_service.search_by_subject.return_value = [candidate("/works/A")]

        service.get_recommendations(ID_USER, genre="Fantasy")

        rec_dao.find_top_rated_books.assert_called_once()
        rec_dao.get_average_ratings.assert_not_called()
        book_service.save_book.assert_not_called()

    def test_empty_open_library_result_uses_fallback(
        self,
        service: RecommendationService,
        rec_dao: Mock,
    ) -> None:
        """If Open Library returns nothing, the fallback is used."""
        service.get_recommendations(ID_USER, genre="Fantasy")

        rec_dao.find_top_rated_books.assert_called_once()

    def test_fallback_is_sorted(
        self,
        service: RecommendationService,
        rec_dao: Mock,
    ) -> None:
        """Fallback results follow the sort parameter."""
        rec_dao.find_top_rated_books.return_value = [
            (make_book(1, "Zorro"), 5.0),
            (make_book(2, "Apple"), 4.0),
        ]

        result = service.get_recommendations(ID_USER, sort="title")

        assert [r.book.title for r in result] == ["Apple", "Zorro"]

    def test_fallback_empty(
        self,
        service: RecommendationService,
    ) -> None:
        """Nothing anywhere gives an empty list."""
        assert service.get_recommendations(ID_USER) == []


class TestRecommendationModel:
    """Tests for the Recommendation model."""

    def test_score_above_five_rejected(self) -> None:
        """A score must be between 0 and 5."""
        with pytest.raises(ValidationError):
            Recommendation(book=make_book(1), score=6.0, reason="x")

    def test_score_can_be_none(self) -> None:
        """An unrated book has no score."""
        rec = Recommendation(book=make_book(1), score=None, reason="x")
        assert rec.score is None
