import math
from typing import List, Tuple, Optional

from disnake import Embed, Component, User
from tortoise.exceptions import DoesNotExist

from app.config import config, logger
from app.core.enums import ItemType
from app.core.models import Item, User
from app.utils.ui_utils import ui_utils


class InventoryService:

    @staticmethod
    async def get_user_items(user_id: int, limit: int, offset: int = 0) -> Tuple[List[Item], bool, bool]:
        user = await User.get(user_id=user_id).prefetch_related("inventory")
        items_query = user.inventory.all().order_by("id").offset(offset).limit(limit + 1)
        items_raw = await items_query

        has_next = len(items_raw) > limit
        current_page_items = items_raw[:limit]
        has_previous = offset > 0

        return current_page_items, has_previous, has_next

    @staticmethod
    async def get_total_user_items_count(user_id: int) -> int:
        user = await User.get(user_id=user_id)
        return await user.inventory.all().count()

    @staticmethod
    async def get_last_page_offset(total_count: int, limit: int) -> Tuple[int, int]:
        if total_count == 0:
            return 0, 1
        total_pages = math.ceil(total_count / limit)
        offset = max(0, (total_pages - 1) * limit)
        return offset, total_pages

    @staticmethod
    async def check_for_default_card(user: User) -> None:
        if not config.cards:
            return

        default_card_id = list(config.cards.keys())[-1]
        has_default_card = await user.inventory.filter(item_id=default_card_id).exists()

        if not has_default_card:
            try:
                default_item = await Item.get(item_id=default_card_id)
                await user.inventory.add(default_item)
            except DoesNotExist:
                logger.error(f"Error: Default item '{default_card_id}' not found in the database.")

    async def init_inventory_message(self, user: User) -> Optional[Tuple[Embed, List[Component]]]:
        items, _, has_next = await self.get_user_items(user.id, limit=config.inventory_items_per_page)

        embed = await ui_utils.format_inventory_embed(user, items)

        components = await ui_utils.init_control_buttons(
            criteria="inventory",
            disable_first_page_button=True,
            disable_previous_page_button=True,
            disable_next_page_button=not has_next,
            disable_last_page_button=not has_next
        )
        return embed, components

    async def edit_inventory_message(self, user: User, page: int, offset: int) -> Optional[
        Tuple[Embed, List[Component]]]:
        items, has_previous, has_next = await self.get_user_items(
            user.id, limit=config.inventory_items_per_page, offset=offset
        )

        embed = await ui_utils.format_inventory_embed(user, items, offset=offset)

        components = await ui_utils.init_control_buttons(
            criteria="inventory",
            current_page_text=page,
            disable_first_page_button=not has_previous,
            disable_previous_page_button=not has_previous,
            disable_next_page_button=not has_next,
            disable_last_page_button=not has_next
        )
        return embed, components

    @staticmethod
    async def equip_item(user_id: int, item_id: str) -> str:
        user = await User.get(user_id=user_id)

        try:
            item_to_equip = await user.inventory.filter(item_id=item_id).get()
        except DoesNotExist:
            return "У вас немає такого предмета в інвентарі"

        if item_to_equip.item_type != ItemType.CARD:
            return "Цей предмет неможливо екіпірувати"

        if user.equipped_card_id == item_to_equip.id:
            return "Ви вже екіпірували даний предмет"

        user.equipped_card_id = item_to_equip.id
        await user.save(update_fields=["equipped_card_id"])

        return f"Ви успішно екіпірували картку!"


inventory_service = InventoryService()
