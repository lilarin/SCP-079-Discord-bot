import asyncio
from typing import List, Tuple
from typing import Optional

from disnake import Embed, File, Role, ButtonStyle, User
from disnake.ui import ActionRow, Button

from app.config import config
from app.core.models import SCPObject, Item


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

        if top_users:
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
        else:
            embed.description = "Поки тут нікого немає, це твій шанс!"
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
        buttons = [
            Button(
                style=ButtonStyle.grey,
                label="🡸",
                custom_id=f"first_page_{criteria}_button",
                disabled=disable_first_page_button,
            ),
            Button(
                style=ButtonStyle.grey,
                label="❮",
                custom_id=f"previous_page_{criteria}_button",
                disabled=disable_previous_page_button,
            ),
            Button(
                style=ButtonStyle.grey,
                label=str(current_page_text),
                custom_id=f"current_page_{criteria}_button",
                disabled=True,
            ),
            Button(
                style=ButtonStyle.grey,
                label="❯",
                custom_id=f"next_page_{criteria}_button",
                disabled=disable_next_page_button,
            ),
            Button(
                style=ButtonStyle.grey,
                label="🡺",
                custom_id=f"last_page_{criteria}_button",
                disabled=disable_last_page_button,
            )
        ]

        return ActionRow(*buttons) if not all(button.disabled for button in buttons) else None

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
                f"-# ID: `{item.item_id}`"
            ]
            description_lines.append("\n".join(item_details))

        embed.description = "\n\n".join(description_lines)
        embed.set_thumbnail(url="https://imgur.com/XmqvWK9.png")
        return embed

    @staticmethod
    async def format_inventory_embed(user: User, items: List[Item], offset: int = 0) -> Embed:
        embed = Embed(
            title="Інвентар",
            color=0xffffff
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        if not items:
            embed.description = "Ваш інвентар порожній"
            return embed

        description = []
        for i, item in enumerate(items):
            description.append(
                f"{offset + i + 1}. **{item.name}**\n"
                f"-# **{item.description}**\n"
                f"-# ID: `{item.item_id}`"
            )

        embed.description = "\n\n".join(description)
        return embed

    @staticmethod
    async def format_legal_work_embed(prompt: str, reward: int) -> Embed:
        embed = Embed(
            title="Результат роботи",
            description=f"{prompt}\n\n-# **Зароблено:** {reward} 💠",
            color=0x4CAF50
        )
        return embed

    @staticmethod
    async def format_non_legal_work_embed(prompt: str, amount: int, is_success: bool) -> Embed:
        if is_success:
            title = "Результат ризикованої роботи"
            description = f"{prompt}\n\n-# **Зароблено:** {amount} 💠"
            color = 0x4CAF50
        else:
            title = "Результат ризикованої роботи"
            description = f"{prompt}\n\n-# **Втрачено:** {amount} 💠"
            color = 0xE53935

        embed = Embed(
            title=title,
            description=description,
            color=color
        )
        return embed

    @staticmethod
    async def format_crystallize_embed(
            bet: int, multiplier: float, potential_win: int, loss_chance: float, is_first_turn: bool
    ) -> Tuple[Embed, List[ActionRow]]:
        embed = Embed(
            title="Процес Кристалізації",
            description=(
                "Ваша ставка кристалізується\n"
                "Збільшуйте множник, але пам'ятайте про ризик!"
            ),
            color=0xFFB9BC
        )
        embed.set_thumbnail(url="https://imgur.com/DOAsTfy.png")

        buttons = [
            Button(
                style=ButtonStyle.secondary,
                label=f"Ставка: {bet} 💠",
                custom_id="display_bet",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=f"Множник: x{multiplier:.2f}",
                custom_id="display_multiplier",
                disabled=True),
            Button(
                style=ButtonStyle.secondary,
                label=f"Шанс провалу: {loss_chance:.1f}%",
                custom_id="display_loss",
                disabled=True)
        ]
        state_row = ActionRow(*buttons)

        continue_button = Button(
            style=ButtonStyle.primary,
            label="Кристалізувати далі",
            custom_id="game_crystallize_continue"
        )
        stop_button = Button(
            style=ButtonStyle.green,
            label=f"Забрати {potential_win} 💠",
            custom_id="game_crystallize_stop",
            disabled=is_first_turn
        )
        action_row = ActionRow(continue_button, stop_button)

        return embed, [state_row, action_row]

    @staticmethod
    async def format_crystallize_win_embed(bet: int, winnings: int, multiplier: float) -> Embed:
        embed = Embed(
            title="Процес зупинено!",
            description=(
                f"Ви вчасно зупинили кристалізацію та зафіксували свій прибуток!\n\n"
                f"-# **Ваша ставка:** {bet} 💠\n"
                f"-# **Підсумковий множник:** x{multiplier:.2f}\n"
                f"-# **Виграш:** {winnings} 💠"
            ),
            color=0x4CAF50
        )
        embed.set_thumbnail(url="https://imgur.com/DOAsTfy.png")
        return embed

    @staticmethod
    async def format_crystallize_loss_embed(bet: int) -> Embed:
        embed = Embed(
            title="Повна кристалізація!",
            description=(
                f"Жадібність взяла гору\nКристал повністю поглинув вашу ставку\n\n"
                f"-# **Втрачено:** {bet} 💠"
            ),
            color=0xE53935
        )
        embed.set_thumbnail(url="https://imgur.com/DOAsTfy.png")
        return embed

    @staticmethod
    async def format_coin_flip_win_embed(bet: int) -> Embed:
        embed = Embed(
            title="Перемога!",
            description=(
                f"Вам пощастило, продовжимо?\n\n"
                f"-# **Виграш:** {bet} 💠"
            ),
            color=0x4CAF50
        )
        embed.set_thumbnail(url="https://static.wikia.nocookie.net/scp-secret-laboratory-official/images/f/f0/Coin.PNG/revision/latest?cb=20200413205841")
        return embed

    @staticmethod
    async def format_coin_flip_loss_embed(bet: int) -> Embed:
        embed = Embed(
            title="Програш!",
            description=(
                f"Не пощастило, спробуйте ще\n\n"
                f"-# **Втрачено:** {bet} 💠"
            ),
            color=0xE53935
        )
        embed.set_thumbnail(url="https://static.wikia.nocookie.net/scp-secret-laboratory-official/images/f/f0/Coin.PNG/revision/latest?cb=20200413205841")
        return embed


ui_utils = UIUtils()
