# Use Case Diagram - Ex-Libris

Mermaid has no native use case diagram, so this one is drawn as a flowchart: circles are actors, rounded boxes are use cases, and dotted `extend` / `include` arrows follow UML (from the extension to the base use case, from the base to the included one).

Three actors:

- **Visitor**: not logged in; can only sign up or log in.
- **Reader**: a logged-in user; every other feature requires an account.
- **Admin**: a reader with `is_admin = TRUE`, who can also moderate.

```mermaid
flowchart LR
    Visitor((Visitor))
    Reader((Reader))
    Admin((Admin))
    OL[[Open Library API]]

    Admin -- is a --> Reader

    subgraph Account
        SignUp([Sign up])
        LogIn([Log in])
        LogOut([Log out])
        Settings([Manage my account])
        EditProfile([Edit profile: username,<br/>email, bio, picture])
        ChangePassword([Change password])
        Preferences([Choose theme day / night<br/>and profile visibility])
    end

    subgraph Books
        Search([Search a book])
        Catalogue([Browse the catalogue])
        FilterCatalogue([Filter by genre or author])
        BookPage([View a book page])
        Editions([View its editions])
        ReadReviews([Read reviews and average rating])
    end

    subgraph Library
        ManageLibrary([Manage my library])
        AddBook([Add a book with a status])
        ChangeStatus([Change reading status])
        Dates([Set start and finish dates])
        LikeFav([Like / favorite a book])
        RemoveBook([Remove a book])
        WriteReview([Write, edit or delete<br/>my review])
    end

    subgraph Playlists
        ManagePlaylists([Manage my playlists])
        CreatePlaylist([Create, rename, delete a playlist])
        PlaylistBooks([Add / remove books])
    end

    subgraph Discover
        Recommend([Get recommendations])
        RecGenre([Choose a genre])
        RecSort([Sort by rating, newest or title])
    end

    subgraph Progress
        MyProgress([View my progress])
        Stats([Reading statistics])
        Quests([Quests])
        Achievements([Achievements])
        Wheel([Genre wheel])
    end

    subgraph Readers
        FindReaders([Search readers])
        ViewReader([View a reader's profile])
        ReaderContent([See their library, playlists,<br/>stats, genre wheel, reviews])
        Follow([Follow / unfollow])
        FollowLists([See followers and following])
    end

    subgraph Moderation
        Suspend([Suspend a reader 1-365 days])
        Ban([Ban a reader])
        DeleteAnyReview([Delete any review])
    end

    Visitor --- SignUp
    Visitor --- LogIn

    Reader --- LogOut
    Reader --- Settings
    Reader --- Search
    Reader --- Catalogue
    Reader --- ManageLibrary
    Reader --- ManagePlaylists
    Reader --- Recommend
    Reader --- MyProgress
    Reader --- FindReaders

    Admin --- Suspend
    Admin --- Ban
    Admin --- DeleteAnyReview

    EditProfile -. extend .-> Settings
    ChangePassword -. extend .-> Settings
    Preferences -. extend .-> Settings

    Search -. include .-> OL
    FilterCatalogue -. extend .-> Catalogue
    BookPage -. extend .-> Search
    BookPage -. extend .-> Catalogue
    Editions -. extend .-> BookPage
    ReadReviews -. extend .-> BookPage
    Editions -. include .-> OL

    AddBook -. extend .-> ManageLibrary
    ChangeStatus -. extend .-> ManageLibrary
    Dates -. extend .-> ManageLibrary
    LikeFav -. extend .-> ManageLibrary
    RemoveBook -. extend .-> ManageLibrary
    WriteReview -. extend .-> ManageLibrary

    CreatePlaylist -. extend .-> ManagePlaylists
    PlaylistBooks -. extend .-> ManagePlaylists

    RecGenre -. extend .-> Recommend
    RecSort -. extend .-> Recommend
    Recommend -. include .-> OL

    Stats -. extend .-> MyProgress
    Quests -. extend .-> MyProgress
    Achievements -. extend .-> MyProgress
    Wheel -. extend .-> MyProgress

    ViewReader -. extend .-> FindReaders
    ReaderContent -. extend .-> ViewReader
    Follow -. extend .-> ViewReader
    FollowLists -. extend .-> ViewReader
```

Notes:

- **Private profiles**: when a reader sets their profile to private, other readers still see their name, bio and picture, but get a 403 on their library, playlists, stats and genre wheel. Reviews stay public because they are also shown on book pages.
- **Reviews**: a reader can only review a book that is in their own library, and only once per book (see [activity_diagram_f4.md](activity_diagram_f4.md)).
- **Moderation**: an admin cannot suspend or ban themselves or another admin. A banned or suspended reader is logged out on their next request.
