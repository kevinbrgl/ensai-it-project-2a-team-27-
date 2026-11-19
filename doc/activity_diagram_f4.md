# Activity Diagram - F4: Reviews

Routes: `GET /api/books/{book_id}/reviews`, `POST /api/books/{book_id}/reviews`, `PUT /api/reviews/{review_id}`, `DELETE /api/reviews/{review_id}`, `GET /api/users/{user_id}/reviews` (`reviews_routes.py`, `ReviewService`) and, for admins, `DELETE /api/admin/reviews/{review_id}` (`admin_routes.py`, `AdminService`).

A review is a rating from 1 to 5 with an optional comment of at most 2000 characters.

```mermaid
flowchart TD
    Start([Start: user on a book page]) --> Action{Choose action}

    %% ===== View =====
    Action -- View --> BookExists{Book exists?}
    BookExists -- No --> NotFound[404: Book not found.] --> End
    BookExists -- Yes --> ShowReviews[Show the reviews,<br/>the average rating and the number of reviews] --> End

    %% ===== Write =====
    Action -- Write --> WriteForm[Enter rating 1-5 and comment]
    WriteForm --> WriteValid{Rating 1-5 and<br/>comment of 2000 chars max?}
    WriteValid -- No --> Invalid[422: Invalid fields] --> WriteForm
    WriteValid -- Yes --> InLibrary{Book in the<br/>user's library?}
    InLibrary -- No --> NotInLibrary[403: You can only review a book<br/>from your library.] --> End
    InLibrary -- Yes --> AlreadyReviewed{Already reviewed<br/>this book?}
    AlreadyReviewed -- Yes --> Conflict[409: You have already reviewed this book.] --> End
    AlreadyReviewed -- No --> SaveNew[Save the review] --> End

    %% ===== Edit / delete =====
    Action -- Edit --> EditForm[Change rating and/or comment] --> ReviewExists
    Action -- Delete --> ConfirmDelete[Confirm the deletion] --> ReviewExists
    ReviewExists{Review exists?}
    ReviewExists -- No --> NoReview[404: Review not found.] --> End
    ReviewExists -- Yes --> IsAuthor{User is the author?}
    IsAuthor -- No --> Forbidden[403: You are not the author of this review.] --> End
    IsAuthor -- Yes --> SaveChanges[Save the changes<br/>or delete the review] --> End

    %% ===== Moderation =====
    Action -- Moderate --> IsAdmin{User is an admin?}
    IsAdmin -- No --> AdminOnly[403: Administrator rights required.] --> End
    IsAdmin -- Yes --> AdminDelete{Review exists?}
    AdminDelete -- No --> NoReview
    AdminDelete -- Yes --> AdminRemove[Delete the review,<br/>whoever wrote it] --> End

    End([End])
```
