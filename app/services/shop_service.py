import random

from app.config import config, logger
from app.models import Item, ItemType


class ShopService:
    def __init__(self):
        self.card_configs = config.cards

    async def sync_card_items(self) -> None:
        logger.info("Starting shop card items synchronization...")

        if not self.card_configs:
            logger.error("Card config is empty. Skipping synchronization.")
            return

        existing_items = {
            item.template_id: item async for item in Item.filter(item_type=ItemType.CARD)
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
                logger.info(f"Item '{card_config.name}' ({template_id}) not found. Staging for creation.")
                new_item = Item(
                    template_id=template_id,
                    name=card_config.name,
                    description=card_config.description,
                    price=card_config.price,
                    item_type=ItemType.CARD,
                    quantity=new_quantity
                )
                items_to_create.append(new_item)

        if items_to_create:
            await Item.bulk_create(items_to_create)
            logger.info(f"Successfully created {len(items_to_create)} new card item(s).")

        if items_to_update:
            await Item.bulk_update(items_to_update, fields=["quantity"])
            logger.info(f"Successfully updated quantities for {len(items_to_update)} existing card item(s).")

        total_synced = len(items_to_create) + len(items_to_update)
        if total_synced == 0:
            logger.info("All card items are already up-to-date. No changes made.")
        else:
            logger.info("Shop synchronization complete.")


shop_service = ShopService()
