"""Data Access Object for revoked tokens."""

from datetime import datetime

from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.utils.exceptions import DAOError


class TokenDAO:
    """DAO class for the revoked tokens table.

    :attr cur: Database cursor (RealDictCursor)
    """

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize TokenDAO with a database cursor.

        :param cursor: Database cursor
        """
        self.cur = cursor

    def revoke(self, token_hash: str, expires_at: datetime) -> None:
        """Store a token hash in the revoked list (no error if present).

        :param token_hash: SHA-256 hash of the token
        :param expires_at: Expiration date of the token
        :raises DAOError: If a DB error occurs
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
        """Tell whether a token hash is in the revoked list.

        :param token_hash: SHA-256 hash of the token
        :raises DAOError: If a DB error occurs
        :return: True if the token is revoked
        """
        try:
            self.cur.execute(
                "SELECT 1 FROM revoked_tokens WHERE token_hash = %s",
                (token_hash,),
            )
            return self.cur.fetchone() is not None
        except DBError as exc:
            raise DAOError from exc
