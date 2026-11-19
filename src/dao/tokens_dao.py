"""Database access for revoked token hashes."""

from datetime import datetime

from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.utils.exceptions import DAOError


class TokenDAO:
    """Store and look up revoked token hashes.

    Attributes
    ----------
    cur : RealDictCursor
        PostgreSQL cursor that fetches rows as dictionaries.

    """

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize TokenDAO with a database cursor.

        Parameters
        ----------
        cursor : RealDictCursor
            Database cursor that yields rows as dictionaries.

        """
        self.cur = cursor

    def revoke(self, token_hash: str, expires_at: datetime) -> None:
        """Add a token hash to the revoked list.

        A previously stored hash retains its original expiration time.

        Parameters
        ----------
        token_hash : str
            SHA-256 hash of the token.
        expires_at : datetime
            Expiration date and time of the token.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                """
                INSERT INTO revoked_tokens (token_hash, expires_at)
                VALUES (%s, %s)
                ON CONFLICT (token_hash) DO NOTHING
                """,
                (token_hash, expires_at),
            )
        except DBError as exc:
            raise DAOError from exc

    def is_revoked(self, token_hash: str) -> bool:
        """Check whether a token hash is on the revoked list.

        Parameters
        ----------
        token_hash : str
            SHA-256 hash of the token.

        Returns
        -------
        bool
            True if the token hash is present, or False otherwise.

        Raises
        ------
        DAOError
            If a database error occurs.

        """
        try:
            self.cur.execute(
                "SELECT 1 FROM revoked_tokens WHERE token_hash = %s",
                (token_hash,),
            )
            return self.cur.fetchone() is not None
        except DBError as exc:
            raise DAOError from exc
