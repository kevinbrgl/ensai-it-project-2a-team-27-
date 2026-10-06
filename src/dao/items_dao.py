"""Data Access Object for item operations.

This module provides CRUD operations for items in the database.
All database errors are wrapped in DAOError.
"""
from psycopg2 import Error as DBError
from psycopg2.extras import RealDictCursor

from src.models import Item, ItemCreate, ItemUpdate
from src.utils.exceptions import DAOError


class ItemDAO:
    """DAO class for item CRUD operations.

    :param cursor: Database cursor
    """

    def __init__(self, cursor: RealDictCursor) -> None:
        """Initialize ItemDAO with a database cursor.

        :param cursor: Database cursor
        """
        self.cur = cursor

    def create(self, item_create: ItemCreate) -> Item:
        """Create a new item in the database.

        :param item_create: Data for item creation
        :raises DAOError: Raised if item creation fails or DB error occurs
        :return: The created Item object
        """
        try:
            self.cur.execute(
                """
                INSERT INTO items (name, description, user_id)
                VALUES (%(name)s, %(description)s, %(user_id)s)
                RETURNING *
                """,
                item_create.model_dump(),
            )
            row = self.cur.fetchone()
            if row is None:
                msg = "Item creation failed"
                raise DAOError(msg)
            return Item(**row)
        except DBError as exc:
            raise DAOError from exc

    def read(self, item_id: int) -> Item | None:
        """Read an item by its ID.

        :param item_id: ID of the item to read
        :raises DAOError: Raised if DB error occurs
        :return: The Item object or None if not found
        """
        try:
            self.cur.execute(
                """
                SELECT id, name, description, user_id
                FROM items
                WHERE id = %s
                """,
                (item_id,),
            )
            row = self.cur.fetchone()
            return Item(**row) if row else None
        except DBError as exc:
            raise DAOError from exc

    def read_by_user(self, user_id: int) -> list[Item]:
        """Read all items belonging to a user.

        :param user_id: ID of the user
        :raises DAOError: Raised if DB error occurs
        :return: List of Item objects
        """
        try:
            self.cur.execute(
                """
                SELECT id, name, description, user_id
                FROM items
                WHERE user_id = %s
                """,
                (user_id, ),
            )
            rows = self.cur.fetchall()
            return [Item(**row) for row in rows]
        except DBError as exc:
            raise DAOError from exc

    def update(self, item_id: int, item_in: ItemUpdate) -> Item | None:
        """Update an item by its ID.

        :param item_id: ID of the item to update
        :param item_in: Data for item update
        :raises ValueError: Raised if no data to update
        :raises DAOError: Raised if DB error occurs
        :return: The updated Item object or None if not found
        """
        data = item_in.model_dump(exclude_unset=True)

        if data is None:
            msg = "Nothing to update"
            raise ValueError(msg)

        set_clause = ", ".join(f"{key} = %s" for key in data)
        values = [*list(data.values()), item_id]

        try:
            self.cur.execute(
                f"""
                UPDATE items
                SET {set_clause}
                WHERE id = %s
                RETURNING *
                """,  # noqa : S608
                values,
            )
            row = self.cur.fetchone()
            return Item(**row) if row else None
        except DBError as exc:
            raise DAOError from exc

    def delete(self, item_id: int) -> Item | None:
        """Delete an item by its ID.

        :param item_id: ID of the item to delete
        :raises DAOError: Raised if DB error occurs
        :return: The deleted Item object or None if not found
        """
        try:
            self.cur.execute(
                """
                DELETE FROM items
                WHERE id = %s
                RETURNING *
                """,
                (item_id,),
            )
            row = self.cur.fetchone()
            return Item(**row) if row else None
        except DBError as exc:
            raise DAOError from exc
