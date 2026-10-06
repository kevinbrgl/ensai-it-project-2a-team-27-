"""Service layer for item operations.

This module provides business logic for items.
Exceptions are raised for not found or unauthorized access.
"""

from src.dao.items_dao import ItemDAO
from src.models import Item, ItemCreate, ItemRegister, ItemUpdate
from src.utils.exceptions import (
    ItemNotFoundError,
    WrongUserItemError,
)


class ItemService:
    """Service class for item business logic.

    :attr dao: Associated ItemDAO object
    """

    def __init__(self, item_dao: ItemDAO) -> None:
        """Initialize ItemService with a database cursor.

        :param cursor: Database cursor
        """
        self.dao = item_dao

    def register(self, user_id: int, item_in: ItemRegister) -> Item:
        """Register a new item for a user.

        :param user_id: ID of the user
        :param item_in: Item registration data
        :return: The created Item object
        """
        item_create = ItemCreate.model_validate(
            {
                **item_in.model_dump(),
                "user_id": user_id,
            },
            from_attributes=True,
        )
        return self.dao.create(item_create)

    def read(self, user_id: int, item_id: int) -> Item:
        """Read an item by its ID for a user.

        :param user_id: ID of the user
        :param item_id: ID of the item to read
        :raises ItemNotFoundError: Raised if item is not found
        :raises WrongUserItemError: Raised if item does not belong to user
        :return: The requested Item object
        """
        item = self.dao.read(item_id)
        if item is None:
            raise ItemNotFoundError(item_id)
        if item.user_id != user_id:
            raise WrongUserItemError
        return item

    def read_by_user(self, user_id: int) -> list[Item]:
        """Read all items belonging to a user.

        :param user_id: ID of the user
        :raises ItemNotFoundError: Raised if no items are found for user
        :return: List of Item objects
        """
        items = self.dao.read_by_user(user_id)
        if not items:
            raise ItemNotFoundError(user_id=user_id)
        return items

    def update(self, user_id: int, item_id: int, item_in: ItemUpdate) -> Item:
        """Update an item for a user.

        :param user_id: ID of the user
        :param item_id: ID of the item to update
        :param item_in: Item update data
        :raises ItemNotFoundError: Raised if item is not found
        :raises WrongUserItemError: Raised if item does not belong to user
        :return: The updated Item object
        """
        item = self.dao.read(item_id)
        if item is None:
            raise ItemNotFoundError(item_id)
        if item.user_id != user_id:
            raise WrongUserItemError
        updated_item = self.dao.update(item_id, item_in)
        if updated_item is None:
            raise ItemNotFoundError(item_id)
        return updated_item

    def delete(self, user_id: int, item_id: int) -> Item:
        """Delete an item for a user.

        :param user_id: ID of the user
        :param item_id: ID of the item to delete
        :raises ItemNotFoundError: Raised if item is not found
        :raises WrongUserItemError: Raised if item does not belong to user
        :return: The deleted Item object
        """
        item = self.dao.read(item_id)
        if item is None:
            raise ItemNotFoundError(item_id)
        if item.user_id != user_id:
            raise WrongUserItemError
        deleted_item = self.dao.delete(item_id)
        if deleted_item is None:
            raise ItemNotFoundError(item_id)
        return deleted_item
