"""Routes for reviews and ratings (F4) in the FastAPI application."""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from src.api.deps import CurrentUser, ReviewServiceDep
from src.models.reviews import (
    BookReviews,
    ReviewCreate,
    ReviewRead,
    ReviewUpdate,
)
from src.utils.exceptions import (
    BookNotFoundError,
    DAOError,
    NotReviewAuthorError,
    ReviewAlreadyExistsError,
    ReviewNotFoundError,
    UserNotFoundError,
)

router = APIRouter(tags=["Reviews"])
logger = logging.getLogger(__name__)

BookId = Annotated[int, Path(ge=1, description="Database ID of the book")]
ReviewId = Annotated[int, Path(ge=1, description="Database ID of the review")]
UserId = Annotated[int, Path(ge=1, description="Database ID of the user")]


@router.get("/books/{book_id}/reviews")
def get_book_reviews(
    book_id: BookId,
    service: ReviewServiceDep,
    _current_user: CurrentUser,
) -> BookReviews:
    """View a book's reviews, plus its average rating.

    :param book_id: ID of the book
    :param service: Review service dependency
    :param _current_user: Authenticated user dependency
    :raises HTTPException: 404 if the book does not exist,
        500 on database error
    :return: The reviews, the average rating and the number of reviews
    """
    try:
        return service.get_book_reviews(book_id)

    except BookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found.",
        ) from None

    except DAOError:
        logger.exception("Failed to list reviews of book %s", book_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not list the reviews.",
        ) from None


@router.post(
    "/books/{book_id}/reviews",
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    book_id: BookId,
    review_in: ReviewCreate,
    service: ReviewServiceDep,
    current_user: CurrentUser,
) -> ReviewRead:
    """Write a review with a rating (1-5) and a comment.

    :param book_id: ID of the book
    :param review_in: Rating and comment of the review
    :param service: Review service dependency
    :param current_user: The authenticated user
    :raises HTTPException: 404 if the book does not exist,
        409 if the user already reviewed it, 500 on database error
    :return: The created review
    """
    try:
        return service.create_review(
            current_user.id_user,
            book_id,
            review_in,
        )

    except BookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found.",
        ) from None

    except ReviewAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this book.",
        ) from None

    except DAOError:
        logger.exception(
            "Failed to create review on book %s for user %s",
            book_id,
            current_user.id_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create the review.",
        ) from None


@router.put("/reviews/{review_id}")
def update_review(
    review_id: ReviewId,
    review_in: ReviewUpdate,
    service: ReviewServiceDep,
    current_user: CurrentUser,
) -> ReviewRead:
    """Edit my review. Returns 403 if I'm not the author.

    :param review_id: ID of the review
    :param review_in: New rating and comment
    :param service: Review service dependency
    :param current_user: The authenticated user
    :raises HTTPException: 404 if the review does not exist,
        403 if the user is not the author, 500 on database error
    :return: The updated review
    """
    try:
        return service.update_review(
            current_user.id_user,
            review_id,
            review_in,
        )

    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found.",
        ) from None

    except NotReviewAuthorError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the author of this review.",
        ) from None

    except DAOError:
        logger.exception("Failed to update review %s", review_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update the review.",
        ) from None


@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_review(
    review_id: ReviewId,
    service: ReviewServiceDep,
    current_user: CurrentUser,
) -> None:
    """Delete my review. Returns 403 if I'm not the author.

    Returns 204 No Content with an empty body when the review is deleted.

    :param review_id: ID of the review
    :param service: Review service dependency
    :param current_user: The authenticated user
    :raises HTTPException: 404 if the review does not exist,
        403 if the user is not the author, 500 on database error
    """
    try:
        service.delete_review(current_user.id_user, review_id)

    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found.",
        ) from None

    except NotReviewAuthorError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the author of this review.",
        ) from None

    except DAOError:
        logger.exception("Failed to delete review %s", review_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete the review.",
        ) from None


@router.get("/users/{user_id}/reviews")
def list_user_reviews(
    user_id: UserId,
    service: ReviewServiceDep,
    _current_user: CurrentUser,
) -> list[ReviewRead]:
    """List a user's reviews.

    :param user_id: ID of the user
    :param service: Review service dependency
    :param _current_user: Authenticated user dependency
    :raises HTTPException: 404 if the user does not exist,
        500 on database error
    :return: The reviews of the user, newest first
    """
    try:
        return service.list_user_reviews(user_id)

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None

    except DAOError:
        logger.exception("Failed to list reviews of user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not list the reviews.",
        ) from None
