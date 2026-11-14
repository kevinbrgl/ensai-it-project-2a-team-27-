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


@router.get(
    "/books/{book_id}/reviews",
    summary="💬 See the reviews of a book",
    responses={
        404: {"description": "Book not found"},
        500: {"description": "Database error"},
    },
)
def get_book_reviews(
    book_id: BookId,
    service: ReviewServiceDep,
    _current_user: CurrentUser,
) -> BookReviews:
    """Return the **reviews** of a book, with its **average rating**.

    🔒 Authentication required

    **Returns:**

    - ⭐ `average_rating`: average of the ratings (`null` if no review)
    - 🔢 `review_count`: number of reviews
    - 💬 `reviews`: the reviews, **newest first**

    **Example response:**

    ```json
    {
      "id_book": 12,
      "average_rating": 4.5,
      "review_count": 2,
      "reviews": [
        {
          "id_review": 7,
          "id_user": 3,
          "id_book": 12,
          "rating": 5,
          "comment": "A must read!",
          "created_at": "2026-01-15T10:30:00"
        }
      ]
    }
    ```
    \f
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
    summary="✍️ Write a review",
    responses={
        404: {"description": "Book not found"},
        409: {"description": "You have already reviewed this book"},
        500: {"description": "Database error"},
    },
)
def create_review(
    book_id: BookId,
    review_in: ReviewCreate,
    service: ReviewServiceDep,
    current_user: CurrentUser,
) -> ReviewRead:
    """Publish a **review** on a book: a rating and a comment.

    🔒 Authentication required

    **Fields:**

    - ⭐ `rating`: a whole number from **1** to **5**
    - 💬 `comment`: optional text, up to 2000 characters

    **Rule:** only **one review per book** for each user. To change
    it, edit your existing review.

    **Example request:**

    ```json
    {
      "rating": 5,
      "comment": "A must read!"
    }
    ```
    \f
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


@router.put(
    "/reviews/{review_id}",
    summary="✏️ Edit my review",
    responses={
        403: {"description": "You are not the author of this review"},
        404: {"description": "Review not found"},
        500: {"description": "Database error"},
    },
)
def update_review(
    review_id: ReviewId,
    review_in: ReviewUpdate,
    service: ReviewServiceDep,
    current_user: CurrentUser,
) -> ReviewRead:
    """Replace the **rating** and the **comment** of your review.

    🔒 Authentication required, **author only**

    **Fields:**

    - ⭐ `rating`: a whole number from **1** to **5** (required)
    - 💬 `comment`: optional text, up to 2000 characters

    **Behaviour:** the review is **fully replaced**. If you do not
    send `comment`, the old comment is erased.

    **Example request:**

    ```json
    {
      "rating": 4,
      "comment": "Still great after a second read."
    }
    ```
    \f
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
    summary="🗑️ Delete my review",
    responses={
        403: {"description": "You are not the author of this review"},
        404: {"description": "Review not found"},
        500: {"description": "Database error"},
    },
)
def delete_review(
    review_id: ReviewId,
    service: ReviewServiceDep,
    current_user: CurrentUser,
) -> None:
    """Delete one of **your reviews**.

    🔒 Authentication required, **author only**

    **Good to know:** after the deletion you can write a **new
    review** on the same book.

    **Response:** `204 No Content`, with an empty body.
    \f
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


@router.get(
    "/users/{user_id}/reviews",
    summary="💬 List the reviews of a user",
    responses={
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def list_user_reviews(
    user_id: UserId,
    service: ReviewServiceDep,
    _current_user: CurrentUser,
) -> list[ReviewRead]:
    """List all the **reviews written by a user**, newest first.

    🔒 Authentication required

    **Use cases:**

    - See what a friend thinks of the books they read
    - Find your own reviews, with your own user ID

    **Good to know:** the list is **empty** when the user has not
    written any review.
    \f
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
