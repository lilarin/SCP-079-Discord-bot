import asyncio
import random
from typing import List, Tuple, Optional

from disnake import Embed, Component, User
from tortoise.exceptions import DoesNotExist
from tortoise.transactions import in_transaction

from app.config import logger
from app.core.models import Item, ItemType, User as UserModel, UserItem, UserAchievement
from app.core.variables import variables
from app.localization import t
from app.services import achievement_handler_service
from app.utils.ui_utils import ui_utils


class ShopService:
    def __init__(self):
        self.card_configs = variables.cards

    async def sync_shop_cards(self) -> None:
        logger.info("Starting shop card metadata synchronization...")

        if not self.card_configs:
            logger.error("Card config is empty. Skipping synchronization")
            return

        existing_items = {
            item.item_id: item async for item in Item.filter(item_type=ItemType.CARD)
        }

        items_to_create = []
        items_to_update = []
        update_fields = set()

        for template_id, card_config in self.card_configs.items():
            if template_id in existing_items:
                item = existing_items[template_id]
                is_updated = False

                if item.name != card_config.name:
                    item.name = card_config.name
                    update_fields.add("name")
                    is_updated = True

                if item.description != card_config.description:
                    item.description = card_config.description
                    update_fields.add("description")
                    is_updated = True

                if item.price != card_config.price:
                    item.price = card_config.price
                    update_fields.add("price")
                    is_updated = True

                if is_updated:
                    items_to_update.append(item)
            else:
                logger.info(f"Item '{card_config.name}' ({template_id}) not found. Staging for creation")
                min_qty, max_qty = card_config.quantity_range
                initial_quantity = random.randint(min_qty, max_qty)

                new_item = Item(
                    item_id=template_id,
                    name=card_config.name,
                    description=card_config.description,
                    price=card_config.price,
                    item_type=ItemType.CARD,
                    quantity=initial_quantity
                )
                items_to_create.append(new_item)

        if items_to_create:
            await Item.bulk_create(items_to_create)
            logger.info(f"Successfully created {len(items_to_create)} new card item(s)")

        if items_to_update:
            await Item.bulk_update(items_to_update, fields=list(update_fields))
            logger.info(f"Successfully updated metadata for {len(items_to_update)} existing card item(s)")

        if not items_to_create and not items_to_update:
            logger.info("All card items are already up-to-date. No changes made")
        else:
            logger.info("Shop data synchronization complete")

    async def update_card_item_quantities(self) -> None:
        if not self.card_configs:
            logger.error("Card config is empty. Skipping quantity update")
            return

        all_card_items = [item async for item in Item.filter(item_type=ItemType.CARD)]

        if not all_card_items:
            logger.warning("No card items found in the database")
            return

        items_for_bulk_update = []
        for item in all_card_items:
            card_config = self.card_configs.get(item.item_id)

            if not card_config:
                continue

            min_qty, max_qty = card_config.quantity_range
            item.quantity = random.randint(min_qty, max_qty)
            items_for_bulk_update.append(item)

        if items_for_bulk_update:
            await Item.bulk_update(items_for_bulk_update, fields=["quantity"])

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

    async def init_shop_message(self) -> Optional[Tuple[Embed, List[Component]]]:
        items, _, has_next = await self.get_shop_items(limit=variables.shop_items_per_page)
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
            limit=variables.shop_items_per_page, offset=offset
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
    async def buy_item(user: User, db_user: UserModel, item_id: str) -> str:
        try:
            item_info = await Item.get(item_id=item_id)
        except DoesNotExist:
            return t("errors.item_not_found")

        async with in_transaction() as conn:
            item = await Item.get(id=item_info.id).using_db(conn).select_for_update()

            if item.quantity <= 0:
                return t("responses.shop.item_out_of_stock")

            if db_user.balance < item.price:
                return t("errors.insufficient_funds_for_purchase", balance=db_user.balance)

            if await UserItem.filter(user=db_user, item=item).exists():
                return t("responses.shop.item_already_owned")

            card_config = variables.cards.get(item_id)
            if card_config and card_config.required_achievements:
                required_ids = set(card_config.required_achievements)
                user_achievements = await UserAchievement.filter(user=db_user).prefetch_related("achievement")
                user_ach_ids = {ua.achievement.achievement_id for ua in user_achievements}

                missing_ids = required_ids - user_ach_ids
                if missing_ids:
                    missing_ach = "\n* ".join(
                        [
                            f"{variables.achievements[ach_id].name} {variables.achievements[ach_id].icon}"
                            for ach_id in missing_ids
                            if ach_id in variables.achievements
                        ]
                    )
                    return t("responses.shop.missing_achievements_start") + f"\n* {missing_ach}"

            db_user.balance -= item.price
            item.quantity -= 1

            await db_user.save(using_db=conn, update_fields=["balance"])
            await item.save(using_db=conn, update_fields=["quantity"])
            await UserItem.create(user=db_user, item=item, using_db=conn)

        asyncio.create_task(achievement_handler_service.handle_shop_achievements(user, item_id))
        return t("responses.shop.buy_success", item_name=item.name)


shop_service = ShopService()
