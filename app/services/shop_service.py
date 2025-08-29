import math
import random
from typing import List, Tuple, Optional

from disnake import Embed, Component
from tortoise.exceptions import DoesNotExist
from tortoise.transactions import in_transaction

from app.config import config, logger
from app.core.models import Item, ItemType, User
from app.utils.ui_utils import ui_utils


class ShopService:
    def __init__(self):
        self.card_configs = config.cards

    async def sync_card_items(self) -> None:
        logger.info("Starting shop card items synchronization...")

        if not self.card_configs:
            logger.error("Card config is empty. Skipping synchronization")
            return

        existing_items = {
            item.item_id: item async for item in Item.filter(item_type=ItemType.CARD)
        }

        items_to_create = []
        items_to_update = []

        for template_id, card_config in self.card_configs.items():
            min_qty, max_qty = card_config.quantity_range
            new_quantity = random.randint(min_qty, max_qty)

            if template_id in existing_items:
                item = existing_items[template_id]
                if item.quantity != new_quantity:
                    item.quantity = new_quantity
                    items_to_update.append(item)
            else:
                logger.info(f"Item '{card_config.name}' ({template_id}) not found. Staging for creation")
                new_item = Item(
                    item_id=template_id,
                    name=card_config.name,
                    description=card_config.description,
                    price=card_config.price,
                    item_type=ItemType.CARD,
                    quantity=new_quantity
                )
                items_to_create.append(new_item)

        if items_to_create:
            await Item.bulk_create(items_to_create)
            logger.info(f"Successfully created {len(items_to_create)} new card item(s)")

        if items_to_update:
            await Item.bulk_update(items_to_update, fields=["quantity"])
            logger.info(f"Successfully updated quantities for {len(items_to_update)} existing card item(s)")

        total_synced = len(items_to_create) + len(items_to_update)
        if total_synced == 0:
            logger.info("All card items are already up-to-date. No changes made")
        else:
            logger.info("Shop synchronization complete")

    @staticmethod
    async def get_shop_items(limit: int, offset: int = 0) -> Tuple[List[Item], bool, bool]:
        items_query = (
            Item.filter(quantity__gt=0)
            .order_by("price")
            .offset(offset)
            .limit(limit + 1)
        )
        items_raw = await items_query

        has_next = len(items_raw) > limit
        current_page_items = items_raw[:limit]
        has_previous = offset > 0

        return current_page_items, has_previous, has_next

    @staticmethod
    async def get_total_items_count() -> int:
        return await Item.filter(quantity__gt=0).count()

    @staticmethod
    async def get_last_page_offset(total_count: int, limit: int) -> Tuple[int, int]:
        if total_count == 0:
            return 0, 1
        total_pages = math.ceil(total_count / limit)
        offset = max(0, (total_pages - 1) * limit)
        return offset, total_pages

    async def init_shop_message(self) -> Optional[Tuple[Embed, List[Component]]]:
        items, _, has_next = await self.get_shop_items(
            limit=config.shop_items_per_page
        )
        embed = await ui_utils.format_shop_embed(items)

        components = await ui_utils.init_control_buttons(
            criteria="shop",
            disable_first_page_button=True,
            disable_previous_page_button=True,
            disable_next_page_button=not has_next,
            disable_last_page_button=not has_next
        )
        return embed, components

    async def edit_shop_message(self, page: int, offset: int) -> Optional[Tuple[Embed, List[Component]]]:
        items, has_previous, has_next = await self.get_shop_items(
            limit=config.shop_items_per_page, offset=offset
        )
        embed = await ui_utils.format_shop_embed(items, offset=offset)

        components = await ui_utils.init_control_buttons(
            criteria="shop",
            current_page_text=page,
            disable_first_page_button=not has_previous,
            disable_previous_page_button=not has_previous,
            disable_next_page_button=not has_next,
            disable_last_page_button=not has_next
        )
        return embed, components

    @staticmethod
    async def buy_item(user_id: int, item_id: str) -> str:
        try:
            item_info = await Item.get(item_id=item_id)
        except DoesNotExist:
            return "Товар з таким ID не знайдено"

        try:
            async with in_transaction() as conn:
                user = await User.get(user_id=user_id).using_db(conn).select_for_update()
                item = await Item.get(id=item_info.id).using_db(conn).select_for_update()

                if item.quantity <= 0:
                    return "Цей товар закінчився"

                if user.balance < item.price:
                    return (
                        "У вас недостатньо коштів\n"
                        f"-# Поточний баланс – {user.balance} 💠"
                    )

                if await user.inventory.filter(id=item.id).exists():
                    return "Ви вже маєте цей предмет у своєму інвентарі"

                card_config = config.cards.get(item_id)
                if card_config and card_config.required_achievements:
                    required_ids = set(card_config.required_achievements)
                    user_ach_ids = set(
                        await user.achievements.all().values_list("achievement_id", flat=True)
                    )

                    missing_ids = required_ids - user_ach_ids
                    if missing_ids:
                        missing_ach = "\n* ".join([
                            f"{config.achievements[ach_id].name} {config.achievements[ach_id].icon}"
                            for ach_id in missing_ids
                            if ach_id in config.achievements
                        ])
                        return (
                            f"Для покупки цього предмета вам не вистачає наступних досягнень:\n* "
                            f"{missing_ach}"
                        )

                user.balance -= item.price
                item.quantity -= 1

                await user.save(using_db=conn, update_fields=['balance'])
                await item.save(using_db=conn, update_fields=['quantity'])
                await user.inventory.add(item, using_db=conn)

                return f"Ви успішно придбали товар **{item.name}**!"
        except Exception as e:
            logger.error(f"Помилка під час транзакції покупки для користувача {user_id}: {e}")
            return "Під час покупки сталася помилка. Спробуйте ще раз"


shop_service = ShopService()
