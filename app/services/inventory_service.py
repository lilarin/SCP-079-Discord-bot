from typing import List, Tuple, Optional

from disnake import Embed, User, Member, ui
from tortoise.exceptions import DoesNotExist

from app.config import logger
from app.core.enums import ItemType
from app.core.models import Item, User as UserModel, UserItem
from app.core.variables import variables
from app.embeds import economy_embeds
from app.localization import t
from app.views.pagination_view import PaginationView


class InventoryService:
    @staticmethod
    async def get_user_items(user_id: int, limit: int, offset: int = 0) -> Tuple[List[Item], bool, bool]:
        user, _ = await UserModel.get_or_create(user_id=user_id)
        user_items_query = (
            UserItem.filter(user=user)
            .select_related("item")
            .order_by("item__id")
            .offset(offset)
            .limit(limit + 1)
        )
        user_items_raw = await user_items_query
        items_raw = [ui_obj.item for ui_obj in user_items_raw]

        has_next = len(items_raw) > limit
        current_page_items = items_raw[:limit]
        has_previous = offset > 0

        return current_page_items, has_previous, has_next

    @staticmethod
    async def get_total_user_items_count(user_id: int) -> int:
        user, _ = await UserModel.get_or_create(user_id=user_id)
        return await UserItem.filter(user=user).count()

    @staticmethod
    async def check_for_default_card(user: UserModel) -> None:
        if not variables.cards:
            return

        default_card_id = list(variables.cards.keys())[-1]
        has_default_card = await UserItem.filter(user=user, item__item_id=default_card_id).exists()

        if not has_default_card:
            try:
                default_item = await Item.get(item_id=default_card_id)
                await UserItem.create(user=user, item=default_item)
            except DoesNotExist:
                logger.error(f"Error: Default item '{default_card_id}' not found in the database.")

    async def init_inventory_message(self, user: User | Member) -> Optional[Tuple[Embed, List[ui.View]]]:
        items, _, has_next = await self.get_user_items(user.id, limit=variables.inventory_items_per_page)
        embed = await economy_embeds.format_inventory_embed(user, items)
        view = PaginationView(
            criteria="inventory",
            disable_first=True,
            disable_previous=True,
            disable_next=not has_next,
            disable_last=not has_next
        )
        return embed, [view] if view.children else []

    async def edit_inventory_message(
            self, user: User | Member, page: int, offset: int
    ) -> Optional[Tuple[Embed, List[ui.View]]]:
        items, has_previous, has_next = await self.get_user_items(
            user.id, limit=variables.inventory_items_per_page, offset=offset
        )
        embed = await economy_embeds.format_inventory_embed(user, items, offset=offset)
        view = PaginationView(
            criteria="inventory",
            current_page=page,
            disable_first=not has_previous,
            disable_previous=not has_previous,
            disable_next=not has_next,
            disable_last=not has_next
        )
        return embed, [view] if view.children else []

    @staticmethod
    async def equip_item(user_id: int, item_id: str) -> str:
        user = await UserModel.get(user_id=user_id)
        try:
            user_item = await UserItem.get(user=user, item__item_id=item_id).select_related("item")
            item_to_equip = user_item.item
        except DoesNotExist:
            return t("errors.item_not_in_inventory")

        if item_to_equip.item_type != ItemType.CARD:
            return t("errors.item_not_equippable")

        if user.equipped_card_id == item_to_equip.id:
            return t("responses.inventory.already_equipped")

        user.equipped_card_id = item_to_equip.id
        await user.save(update_fields=["equipped_card_id"])

        return t("responses.inventory.equip_success")


inventory_service = InventoryService()
