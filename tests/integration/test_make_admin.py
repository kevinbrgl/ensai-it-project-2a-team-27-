"""Check the command that grants administrator rights."""

from uuid import uuid4

from psycopg2.extras import RealDictCursor

from src.make_admin import grant_admin


def test_grant_admin_promotes_only_that_account(
    cursor: RealDictCursor,
) -> None:
    """The named account becomes an admin and the others are unchanged."""
    names = [f"u_{uuid4().hex[:10]}" for _ in range(2)]
    for name in names:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) "
            "VALUES (%s, %s, 'hash')",
            (name, f"{name}@example.com"),
        )

    assert grant_admin(cursor, names[0])

    cursor.execute(
        "SELECT username, is_admin FROM users WHERE username = ANY(%s) "
        "ORDER BY username = %s DESC",
        (names, names[0]),
    )
    assert cursor.fetchall() == [
        {"username": names[0], "is_admin": True},
        {"username": names[1], "is_admin": False},
    ]


def test_grant_admin_unknown_username(cursor: RealDictCursor) -> None:
    """An unknown username changes nothing and is reported."""
    assert not grant_admin(cursor, f"missing_{uuid4().hex[:10]}")
