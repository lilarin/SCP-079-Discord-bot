import asyncio
from typing import List, Tuple
from typing import Optional

from disnake import Embed, File, Role, ButtonStyle
from disnake.ui import ActionRow, Button

from app.config import config
from app.models import SCPObject, Item


class UIUtils:
    @staticmethod
    async def format_leaderboard_embed(
            top_users: List[Tuple[int, int]], top_criteria: str,
            hint: str, symbol: str, color: str, offset: int = 0
    ) -> Embed:
        embed = Embed(
            title=f"Топ користувачів {top_criteria}",
            color=int(color.lstrip("#"), 16),
        )

        from app.bot import bot

        user_fetch_tasks = [bot.get_or_fetch_user(user_id) for user_id, _ in top_users]

        fetched_users = await asyncio.gather(*user_fetch_tasks)

        description_lines = []
        for i, (user_id, count) in enumerate(top_users, 1):
            user = fetched_users[i - 1]
            if user:
                description_lines.append(
                    f"{i + offset}. {user.mention} (`{user.name}`) – **{count} {symbol}**"
                )

        embed.description = "\n".join(description_lines)
        embed.description += f"\n-# {hint}"
        return embed

    @staticmethod
    async def init_control_buttons(
            criteria: str,
            current_page_text: int = 1,
            disable_first_page_button: bool = False,
            disable_previous_page_button: bool = False,
            disable_next_page_button: bool = False,
            disable_last_page_button: bool = False,
    ) -> ActionRow:
        first_page_button = Button(
            style=ButtonStyle.grey,
            label="🡸",
            custom_id=f"first_page_{criteria}_button",
            disabled=disable_first_page_button,
        )
        previous_page_button = Button(
            style=ButtonStyle.grey,
            label="❮",
            custom_id=f"previous_page_{criteria}_button",
            disabled=disable_previous_page_button,
        )
        current_page_button = Button(
            style=ButtonStyle.grey,
            label=str(current_page_text),
            custom_id=f"current_page_{criteria}_button",
            disabled=True,
        )
        next_page_button = Button(
            style=ButtonStyle.grey,
            label="❯",
            custom_id=f"next_page_{criteria}_button",
            disabled=disable_next_page_button,
        )
        last_page_button = Button(
            style=ButtonStyle.grey,
            label="🡺",
            custom_id=f"last_page_{criteria}_button",
            disabled=disable_last_page_button,
        )
        return ActionRow(
            first_page_button, previous_page_button, current_page_button,
            next_page_button, last_page_button,
        )

    @staticmethod
    async def format_new_user_embed(user_mention: str, card: File, color: int) -> Embed:
        embed = Embed(
            description=f"Вітаємо {user_mention} у складі співробітників фонду!",
            color=color
        )
        embed.set_image(file=card)

        return embed

    @staticmethod
    async def format_user_embed(
            card: File, color: int, dossier: Optional[str] = None,
            role: Optional[Role] = None
    ) -> Embed:
        embed = Embed(
            title="Інформація про співробітника фонду",
            color=color
        )
        embed.set_image(file=card)

        if role:
            embed.add_field(name="Посада:", value=role.mention, inline=False)
        if dossier:
            embed.add_field(name="Досьє:", value=dossier, inline=False)

        return embed

    @staticmethod
    async def format_article_embed(
            article: SCPObject, image_file: File
    ) -> Tuple[Embed, ActionRow]:
        embed = Embed(
            color=int(config.scp_class_config[article.object_class][0].lstrip('#'), 16)
        )
        name_confirm = Button(
            style=ButtonStyle.link,
            url=article.link,
            label="Переглянути статтю",
            emoji=config.scp_class_config[article.object_class][1],
        )

        embed.set_image(file=image_file)
        return embed, ActionRow(name_confirm)

    @staticmethod
    async def format_balance_embed(balance: int, reputation: int, position: int) -> Embed:
        embed = Embed(
            title="Баланс репутації користувача",
            description="",
            color=0xffffff
        )

        embed.description += f"Поточний баланс – {balance} 💠 "
        embed.description += f"\n\n-# Загальна кількість заробленої репутації – {reputation} 🔰"

        if position:
            embed.description += f"\n-# **#{position} у рейтингу серед співробітників**"

        return embed

    @staticmethod
    async def format_shop_embed(items: List[Item], offset: int = 0) -> Embed:
        embed = Embed(
            title="Магазин",
            color=0xffffff
        )

        if not items:
            embed.description = "У магазині наразі немає товарів"
            return embed

        description_lines = []
        for i, item in enumerate(items, 1):
            item_details = [
                f"{i + offset}. **{item.name}**",
                f"Ціна: **{item.price}** 💠",
                f"Кількість: **{item.quantity}**",
                f"-# **{item.description}**",
                f"-# ID для покупки: `{item.template_id}`"
            ]
            description_lines.append("\n".join(item_details))

        embed.description = "\n\n".join(description_lines)
        embed.set_thumbnail(
            url="https://media.discordapp.net/attachments/614115775376261120/1402411530548543629/plate_1.png"
        )
        return embed


ui_utils = UIUtils()
