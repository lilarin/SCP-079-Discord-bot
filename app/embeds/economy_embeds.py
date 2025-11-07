from typing import List, Optional

from disnake import Embed, User

from app.core.enums import Color
from app.core.models import Item
from app.core.variables import variables
from app.localization import t


async def format_balance_embed(user_avatar_url: str, balance: int, reputation: int, position: int) -> Embed:
    embed = Embed(
        title=t("ui.balance.title"),
        description="",
        color=Color.WHITE.value
    )

    embed.description += t("ui.balance.current_balance", balance=balance)
    embed.description += t("ui.balance.total_reputation", reputation=reputation)

    if position:
        embed.description += t("ui.balance.rank_position", position=position)

    embed.set_thumbnail(url=user_avatar_url)

    return embed


async def format_shop_embed(items: List[Item], offset: int = 0) -> Embed:
    embed = Embed(
        title=t("ui.shop.title"),
        color=Color.WHITE.value
    )

    if not items:
        embed.description = t("ui.shop.no_items")
        return embed

    description_lines = []
    for i, item in enumerate(items, 1):
        item_details = [
            f"{i + offset}. **{item.name}**",
            t("ui.shop.item_price", price=item.price),
            t("ui.shop.item_quantity", quantity=item.quantity),
            f"-# **{item.description}**",
        ]

        card_config = variables.cards.get(item.item_id)

        if card_config and card_config.required_achievements:
            required_ach = []
            for ach_id in card_config.required_achievements:
                ach_config = variables.achievements.get(ach_id)
                if ach_config:
                    required_ach.append(f"{ach_config.name} {ach_config.icon}")

            if required_ach:
                requirements_str = "\n-# * ".join(required_ach)
                item_details.append(f'{t("ui.shop.required_achievements")} \n-# * {requirements_str}')

        item_details.extend([t("ui.shop.item_id", item_id=item.item_id)])
        description_lines.append("\n".join(item_details))

    embed.description = "\n\n".join(description_lines)
    embed.set_thumbnail(url="https://imgur.com/XmqvWK9.png")
    return embed


async def format_inventory_embed(user: User, items: List[Item], offset: int = 0) -> Embed:
    embed = Embed(
        title=t("ui.inventory.title"),
        color=Color.WHITE.value
    )
    embed.set_thumbnail(url=user.display_avatar.url)

    if not items:
        embed.description = t("ui.inventory.empty")
        return embed

    description = [
        f"{offset + i + 1}. **{item.name}**\n"
        f"-# **{item.description}**\n"
        f'{t("ui.inventory.item_id", item_id=item.item_id)}'
        for i, item in enumerate(items)
    ]

    embed.description = "\n\n".join(description)
    return embed


async def format_legal_work_embed(prompt: str, reward: int) -> Embed:
    return Embed(
        title=t("ui.work.legal_title"),
        description=f'{prompt}\n\n-# {t("ui.work.earned", amount=reward)}',
        color=Color.GREEN.value
    )


async def format_non_legal_work_embed(prompt: str, amount: int, is_success: bool) -> Embed:
    if is_success:
        title = t("ui.work.risky_title")
        description = f'{prompt}\n\n-# {t("ui.work.earned", amount=amount)}'
        color = Color.GREEN.value
    else:
        title = t("ui.work.risky_title")
        description = f'{prompt}\n\n-# {t("ui.work.lost", amount=amount)}'
        color = Color.RED.value

    return Embed(
        title=title,
        description=description,
        color=color
    )


async def format_balance_log_embed(
        user_mention: str,
        avatar_url: Optional[str],
        amount: int,
        new_balance: int,
        reason: str,
        log_id: int
) -> Embed:
    color = Color.GREEN.value if amount > 0 else Color.RED.value
    amount_str = f"+{amount}" if amount > 0 else str(amount)

    embed = Embed(
        description=f"### {user_mention}",
        color=color,
    )

    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    embed.add_field(name=t("ui.balance_log.reason_field"), value=reason, inline=False)
    embed.add_field(name=t("ui.balance_log.amount_field"), value=f"**{amount_str}** 💠", inline=True)
    embed.add_field(name=t("ui.balance_log.new_balance_field"), value=f"**{new_balance}** 💠", inline=True)
    embed.set_footer(text=f"#{log_id}")

    return embed
