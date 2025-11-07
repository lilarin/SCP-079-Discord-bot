import asyncio
import random
from typing import List, Tuple, Optional

from disnake import Embed, User, ui
from tortoise.exceptions import DoesNotExist
from tortoise.transactions import in_transaction

from app.config import logger
from app.core.models import Item, ItemType, User as UserModel, UserItem, UserAchievement
from app.core.variables import variables
from app.embeds import economy_embeds
from app.localization import t
from app.services import achievement_handler_service
from app.views.pagination_view import PaginationView


class ShopService:
    def __init__(self):
        self.card_configs = variables.cards

    async def sync_shop_cards(self) -> None:
        logger.info("Starting shop card metadata synchronization...")
        if not self.card_configs:
            logger.error("Card config is empty. Skipping synchronization")
            return

        existing_items = {item.item_id: item async for item in Item.filter(item_type=ItemType.CARD)}
        items_to_create = []
        items_to_update = []
        update_fields = {"name", "description", "price"}

        for template_id, card_config in self.card_configs.items():
            if template_id in existing_items:
                item = existing_items[template_id]
                if item.name != card_config.name or item.description != card_config.description or item.price != card_config.price:
                    item.name = card_config.name
                    item.description = card_config.description
                    item.price = card_config.price
                    items_to_update.append(item)
            else:
                logger.info(f"Item '{card_config.name}' ({template_id}) not found. Staging for creation")
                min_qty, max_qty = card_config.quantity_range
                items_to_create.append(Item(
                    item_id=template_id, name=card_config.name, description=card_config.description,
                    price=card_config.price, item_type=ItemType.CARD,
                    quantity=random.randint(min_qty, max_qty)
                ))

        if items_to_create:
            await Item.bulk_create(items_to_create)
            logger.info(f"Successfully created {len(items_to_create)} new card item(s)")
        if items_to_update:
            await Item.bulk_update(items_to_update, fields=list(update_fields))
            logger.info(f"Successfully updated metadata for {len(items_to_update)} existing card item(s)")

        logger.info("Shop data synchronization complete")

    async def update_card_item_quantities(self) -> None:
        if not self.card_configs:
            logger.error("Card config is empty. Skipping quantity update")
            return

        all_card_items = await Item.filter(item_type=ItemType.CARD)
        if not all_card_items:
            logger.warning("No card items found in the database")
            return

        for item in all_card_items:
            if card_config := self.card_configs.get(item.item_id):
                min_qty, max_qty = card_config.quantity_range
                item.quantity = random.randint(min_qty, max_qty)

        await Item.bulk_update(all_card_items, fields=["quantity"])

    @staticmethod
    async def get_shop_items(limit: int, offset: int = 0) -> Tuple[List[Item], bool, bool]:
        items_query = Item.filter(quantity__gt=0).order_by("price").offset(offset).limit(limit + 1)
        items_raw = await items_query
        has_next = len(items_raw) > limit
        current_page_items = items_raw[:limit]
        has_previous = offset > 0
        return current_page_items, has_previous, has_next

    @staticmethod
    async def get_total_items_count() -> int:
        return await Item.filter(quantity__gt=0).count()

    async def init_shop_message(self) -> Optional[Tuple[Embed, List[ui.View]]]:
        items, _, has_next = await self.get_shop_items(limit=variables.shop_items_per_page)
        embed = await economy_embeds.format_shop_embed(items)
        view = PaginationView(
            criteria="shop",
            disable_first=True,
            disable_previous=True,
            disable_next=not has_next,
            disable_last=not has_next
        )
        return embed, [view] if view.children else []

    async def edit_shop_message(self, page: int, offset: int) -> Optional[Tuple[Embed, List[ui.View]]]:
        items, has_previous, has_next = await self.get_shop_items(
            limit=variables.shop_items_per_page, offset=offset
        )
        embed = await economy_embeds.format_shop_embed(items, offset=offset)
        view = PaginationView(
            criteria="shop",
            current_page=page,
            disable_first=not has_previous,
            disable_previous=not has_previous,
            disable_next=not has_next,
            disable_last=not has_next
        )
        return embed, [view] if view.children else []

    @staticmethod
    async def buy_item(user: User, db_user: UserModel, item_id: str) -> str:
        try:
            item = await Item.get(item_id=item_id)
        except DoesNotExist:
            return t("errors.item_not_found")

        async with in_transaction() as conn:
            item_for_update = await Item.get(id=item.id).using_db(conn).select_for_update()

            if item_for_update.quantity <= 0:
                return t("responses.shop.item_out_of_stock")
            if db_user.balance < item_for_update.price:
                return t("errors.insufficient_funds_for_purchase", balance=db_user.balance)
            if await UserItem.filter(user=db_user, item=item_for_update).exists():
                return t("responses.shop.item_already_owned")

            card_config = variables.cards.get(item_id)
            if card_config and card_config.required_achievements:
                user_ach_ids = {
                    ua.achievement.achievement_id
                    for ua in await UserAchievement.filter(
                        user=db_user
                    ).prefetch_related("achievement")
                }
                missing_ids = set(card_config.required_achievements) - user_ach_ids
                if missing_ids:
                    missing_ach_names = [
                        f"{variables.achievements[ach_id].name} {variables.achievements[ach_id].icon}"
                        for ach_id in missing_ids if ach_id in variables.achievements
                    ]
                    return t("responses.shop.missing_achievements_start") + "\n* " + "\n* ".join(missing_ach_names)

            db_user.balance -= item_for_update.price
            item_for_update.quantity -= 1
            await db_user.save(using_db=conn, update_fields=["balance"])
            await item_for_update.save(using_db=conn, update_fields=["quantity"])
            await UserItem.create(user=db_user, item=item_for_update, using_db=conn)

        asyncio.create_task(achievement_handler_service.handle_shop_achievements(user, item_id))
        return t("responses.shop.buy_success", item_name=item.name)


shop_service = ShopService()
