"""Routes for item operations in the FastAPI application.

This module provides endpoints for crud operations on items.
All endpoints require authentication and interact with the ItemService layer.
"""
from fastapi import APIRouter, HTTPException, status

from src.api.deps import CurrentUser, CursorDep
from src.dao.items_dao import ItemDAO
from src.models import Item, ItemRegister, ItemUpdate
from src.services.items_service import ItemService
from src.utils.exceptions import (
    DAOError,
    ItemNotFoundError,
    WrongUserItemError,
)

router = APIRouter(prefix="/items", tags=["Items"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def register_item(cursor: CursorDep,
                  current_user: CurrentUser,
                  item_in: ItemRegister) -> Item:
    """Register a new item for the current user.

    :param cursor: Database cursor dependency
    :param current_user: The current authenticated user
    :param item_in: Item registration data
    :raises HTTPException: If item creation fails
    :return: The created Item object
    """
    try:
        return ItemService(ItemDAO(cursor)).register(current_user.id, item_in)
    except DAOError:  # A changer
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user.",
        ) from None


@router.get("/me")
def read_my_items(cursor: CursorDep, current_user: CurrentUser) -> list[Item]:
    """Read all items belonging to the current user.

    :param cursor: Database cursor dependency
    :param current_user: The current authenticated user
    :raises HTTPException: If not items can be found.
    :return: List of Item objects
    """
    try:
        return ItemService(ItemDAO(cursor)).read_by_user(current_user.id)
    except ItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find items for user.",
        ) from None


@router.get("/{item_id}")
def read_item(cursor: CursorDep,
              current_user: CurrentUser,
              item_id: int) -> Item:
    """Read a specific item by its ID for the current user.

    :param cursor: Database cursor dependency
    :param current_user: The current authenticated user
    :param item_id: ID of the item to read
    :raises HTTPException: If unauthorized or not found
    :return: The requested Item object
    """
    try:
        return ItemService(ItemDAO(cursor)).read(current_user.id, item_id)
    except WrongUserItemError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized ressource",
        ) from None
    except ItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        ) from None


@router.patch("/{item_id}")
def update_item(
    cursor: CursorDep, user: CurrentUser, item_id: int, item_in: ItemUpdate,
) -> Item:
    """Update an existing item for the current user.

    :param cursor: Database cursor dependency
    :param user: The current authenticated user
    :param item_id: ID of the item to update
    :param item_in: Item update data
    :raises HTTPException: If unauthorized or not found
    :return: The updated Item object
    """
    try:
        return ItemService(ItemDAO(cursor)).update(user.id, item_id, item_in)
    except WrongUserItemError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized ressource",
        ) from None
    except ItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        ) from None


@router.delete("/{item_id}")
def delete_item(cursor: CursorDep,
                current_user: CurrentUser,
                item_id: int) -> Item:
    """Delete an item by its ID for the current user.

    :param cursor: Database cursor dependency
    :param current_user: The current authenticated user
    :param item_id: ID of the item to delete
    :raises HTTPException: If unauthorized or not found
    :return: The deleted Item object
    """
    try:
        return ItemService(ItemDAO(cursor)).delete(current_user.id, item_id)
    except WrongUserItemError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized ressource",
        ) from None
    except ItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        ) from None
