"""Grant administrator rights to an existing account.

Run from the repository root, where ``.env`` is located::

    uv run python -m src.make_admin <username>
"""

import sys
from contextlib import closing

import psycopg2
from psycopg2.extensions import cursor

from src.core.config import settings

USAGE = "Usage: uv run python -m src.make_admin <username>"


def grant_admin(cur: cursor, username: str) -> bool:
    """Give administrator rights to an account in the caller's transaction.

    Parameters
    ----------
    cur : cursor
        Database cursor of the current transaction.
    username : str
        Username of the account to promote.

    Returns
    -------
    bool
        Whether an account with this username exists.

    """
    cur.execute(
        "UPDATE users SET is_admin = TRUE WHERE username = %s",
        (username,),
    )
    return cur.rowcount == 1


def main() -> None:
    """Promote the account named on the command line."""
    args = sys.argv[1:]
    if len(args) != 1:
        sys.exit(USAGE)
    username = args[0]

    dsn = settings.postgres_dsn.unicode_string()
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        found = grant_admin(cur, username)
    if not found:
        sys.exit(f"No account is named '{username}'. Create it in the app.")
    sys.stdout.write(
        f"{username} is now an administrator. Reload the web app.\n",
    )


if __name__ == "__main__":
    main()
