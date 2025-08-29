import asyncio
from typing import List, Tuple, Optional

from disnake import Embed, File, Role, ButtonStyle, User
from disnake.ui import ActionRow, Button

from app.config import config
from app.core.enums import Color
from app.core.models import SCPObject, Item, Achievement
from app.core.schemas import SCP173GameState, HoleGameState


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
            target_user_id: str = None
    ) -> Optional[ActionRow]:
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
                custom_id=f"current_page_{criteria}_button" if not target_user_id else str(target_user_id),
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
    async def format_balance_embed(user_avatar_url: User, balance: int, reputation: int, position: int) -> Embed:
        embed = Embed(
            title="Баланс репутації користувача",
            description="",
            color=Color.WHITE.value
        )

        embed.description += f"Поточний баланс – {balance} 💠 "
        embed.description += f"\n\n-# Загальна кількість заробленої репутації – {reputation} 🔰"

        if position:
            embed.description += f"\n-# **#{position} у рейтингу серед співробітників**"

        embed.set_thumbnail(url=user_avatar_url)

        return embed

    @staticmethod
    async def format_shop_embed(items: List[Item], offset: int = 0) -> Embed:
        embed = Embed(
            title="Магазин",
            color=Color.WHITE.value
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
            ]

            card_config = config.cards.get(item.item_id)

            if card_config and card_config.required_achievements:

                required_ach = []
                for ach_id in card_config.required_achievements:
                    ach_config = config.achievements.get(ach_id)
                    if ach_config:
                        required_ach.append(f"{ach_config.name} {ach_config.icon}")

                if required_ach:
                    requirements_str = "\n-# * ".join(required_ach)
                    item_details.append(f"-# Необхідні досягнення: \n-# * {requirements_str}")

            item_details.extend([
                f"-# ID: `{item.item_id}`"
            ])
            description_lines.append("\n".join(item_details))

        embed.description = "\n\n".join(description_lines)
        embed.set_thumbnail(url="https://imgur.com/XmqvWK9.png")
        return embed

    @staticmethod
    async def format_inventory_embed(user: User, items: List[Item], offset: int = 0) -> Embed:
        embed = Embed(
            title="Інвентар",
            color=Color.WHITE.value
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        if not items:
            embed.description = "Ваш інвентар порожній"
            return embed

        description = [
            f"{offset + i + 1}. **{item.name}**\n"
            f"-# **{item.description}**\n"
            f"-# ID: `{item.item_id}`"
            for i, item in enumerate(items)
        ]

        embed.description = "\n\n".join(description)
        return embed

    @staticmethod
    async def format_legal_work_embed(prompt: str, reward: int) -> Embed:
        return Embed(
            title="Результат роботи",
            description=f"{prompt}\n\n-# **Зароблено:** {reward} 💠",
            color=Color.GREEN.value
        )

    @staticmethod
    async def format_non_legal_work_embed(prompt: str, amount: int, is_success: bool) -> Embed:
        if is_success:
            title = "Результат ризикованої роботи"
            description = f"{prompt}\n\n-# **Зароблено:** {amount} 💠"
            color = Color.GREEN.value
        else:
            title = "Результат ризикованої роботи"
            description = f"{prompt}\n\n-# **Втрачено:** {amount} 💠"
            color = Color.RED.value

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
            color=Color.LIGHT_PINK.value
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
            color=Color.GREEN.value
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
            color=Color.RED.value
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
            color=Color.GREEN.value
        )
        embed.set_thumbnail(url="https://imgur.com/n4znTOU.png")
        return embed

    @staticmethod
    async def format_coin_flip_loss_embed(bet: int) -> Embed:
        embed = Embed(
            title="Програш!",
            description=(
                f"Не пощастило, спробуйте ще\n\n"
                f"-# **Втрачено:** {bet} 💠"
            ),
            color=Color.RED.value
        )
        embed.set_thumbnail(url="https://imgur.com/n4znTOU.png")
        return embed

    @staticmethod
    async def format_candy_game_embed(
            bet: int, pre_taken_candies: int, player_taken_candies: int,
            potential_win: int, current_multiplier: float,
            swap_colors: bool = False, is_first_turn: bool = False
    ) -> Tuple[Embed, List[ActionRow]]:
        embed = Embed(
            title='SCP-330 – "Візьми тільки дві"',
            description="Ви не можете згадати, чи брали цукерки до цього...",
            color=Color.ORANGE.value
        )
        embed.set_thumbnail(url="https://imgur.com/mGBlbYS.png")

        state_buttons = [
            Button(
                style=ButtonStyle.secondary,
                label=f"Ставка: {bet} 💠",
                custom_id="candy_display_bet",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=f"Множник: x{current_multiplier:.1f}",
                custom_id="candy_display_multiplier",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=f"Ви взяли: {player_taken_candies}",
                custom_id=f"candy_state_{player_taken_candies}_{pre_taken_candies}",
                disabled=True
            ),
        ]
        state_row = ActionRow(*state_buttons)

        take_button_color, leave_button_color = (
            ButtonStyle.primary, ButtonStyle.green
        ) if not swap_colors else (
            ButtonStyle.green, ButtonStyle.primary
        )

        take_button = Button(
            style=take_button_color,
            label="Взяти цукерку",
            custom_id="game_candy_take"
        )
        leave_button = Button(
            style=leave_button_color,
            label=f"Забрати {potential_win} 💠",
            custom_id="game_candy_leave",
            disabled=is_first_turn
        )
        action_row = ActionRow(take_button, leave_button)

        return embed, [state_row, action_row]

    @staticmethod
    async def format_candy_win_embed(winnings: int) -> Embed:
        embed = Embed(
            title="Ви вчасно зупинились!",
            description=(
                f"Ви вирішили не випробовувати долю і пішли\n\n"
                f"-# **Виграш:** {winnings} 💠"
            ),
            color=Color.GREEN.value
        )
        embed.set_thumbnail(url="https://imgur.com/mGBlbYS.png")
        return embed

    @staticmethod
    async def format_candy_loss_embed(bet: int) -> Embed:
        embed = Embed(
            title="Жадібність вас погубила!",
            description=(
                f"Ви взяли забагато цукерок і поплатились за це\n\n"
                f"-# **Втрачено:** {bet} 💠"
            ),
            color=Color.RED.value
        )
        embed.set_thumbnail(url="https://imgur.com/mGBlbYS.png")
        return embed

    @staticmethod
    async def format_coguard_embed(
            bet: int, multiplier: float, potential_win: int, current_number: int,
            win_streak: int, is_first_turn: bool = False
    ) -> Tuple[Embed, List[ActionRow]]:
        embed = Embed(
            title="Протокол когнітивного тесту D-72",
            description=f"**Поточне значення:** `{current_number}`\nЧи буде наступне значення більше чи менше?",
            color=Color.BLUE.value
        )
        embed.set_thumbnail(url="https://imgur.com/pAW9s4O.png")
        state_buttons = [
            Button(
                style=ButtonStyle.secondary,
                label=f"Ставка: {bet} 💠",
                custom_id="coguard_display_bet",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=f"Множник: x{multiplier:.2f}",
                custom_id="coguard_display_multiplier",
                disabled=True),
            Button(
                style=ButtonStyle.secondary,
                label=f"Число: {current_number}",
                custom_id="coguard_display_number",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=f"Правильних відповідей: {win_streak}",
                custom_id="coguard_display_streak",
                disabled=True)
        ]
        state_row = ActionRow(*state_buttons)

        higher_button = Button(
            style=ButtonStyle.primary,
            label="Більше",
            emoji="⬆️",
            custom_id="game_coguard_higher"
        )
        lower_button = Button(
            style=ButtonStyle.primary,
            label="Менше",
            emoji="⬇️",
            custom_id="game_coguard_lower"
        )
        cashout_button = Button(
            style=ButtonStyle.green,
            label=f"Забрати {potential_win} 💠",
            custom_id="game_coguard_cashout",
            disabled=is_first_turn
        )
        action_row = ActionRow(higher_button, lower_button, cashout_button)

        return embed, [state_row, action_row]

    @staticmethod
    async def format_coguard_win_embed(bet: int, winnings: int, multiplier: float, win_streak: int) -> Embed:
        embed = Embed(
            title="Тест успішно пройдено!",
            description=(
                f"Ви вчасно зупинились та підтвердили свою когнітивну стабільність\n\n"
                f"-# **Ваша ставка:** {bet} 💠\n"
                f"-# **Серія правильних відповідей:** {win_streak}\n"
                f"-# **Підсумковий множник:** x{multiplier:.2f}\n"
                f"-# **Виграш:** {winnings} 💠"
            ),
            color=Color.GREEN.value
        )
        embed.set_thumbnail(url="https://imgur.com/pAW9s4O.png")
        return embed

    @staticmethod
    async def format_coguard_loss_embed(bet: int, win_streak: int) -> Embed:
        embed = Embed(
            title="Когнітивний збій!",
            description=(
                f"Ваша інтуїція вас підвела, тест провалено\n\n"
                f"-# **Серія    правильних відповідей:** {win_streak}\n"
                f"-# **Втрачено:** {bet} 💠"
            ),
            color=Color.RED.value
        )
        embed.set_thumbnail(url="https://imgur.com/pAW9s4O.png")
        return embed

    @staticmethod
    async def format_scp173_lobby_embed(game_state: SCP173GameState) -> Embed:
        embed = Embed(
            title="Гра в піжмурки з SCP-173",
            description="**Очікування гравців...**\n\nХто кліпне очима - помре",
            color=Color.WHITE.value
        )
        embed.set_thumbnail(url="https://imgur.com/PJPoIes.png")

        player_list = "\n".join(
            [
                f"{i + 1}. {player.mention}"
                for i, player in enumerate(list(game_state.players))
            ]
        )
        embed.add_field(
            name="Учасники:",
            value=player_list if player_list else "Поки нікого немає...", inline=False
        )
        embed.set_footer(
            text=(
                f"Гра розпочнеться автоматично через "
                f"{config.staring_lobby_duration} секунд, або коли лобі заповниться"
            )
        )
        return embed

    async def init_scp173_lobby_components(self, game_state: SCP173GameState) -> List[ActionRow]:
        is_full = len(game_state.players) >= config.staring_max_players
        state_row = await self.init_scp173_game_components(game_state)

        action_row = ActionRow(
            Button(
                style=ButtonStyle.green,
                label="Приєднатися",
                custom_id="game_scp173_join",
                disabled=is_full
            ),
            Button(
                style=ButtonStyle.primary,
                label="Розпочати гру",
                custom_id="game_scp173_start"
            )
        )

        return [state_row[0], action_row]

    @staticmethod
    async def format_scp173_start_game_embed(game_state: SCP173GameState,
                                             round_logs: Optional[List[dict]] = None) -> Embed:
        player_list = "\n".join(
            [
                f"{i + 1}. {player.mention}"
                for i, player in enumerate(list(game_state.players))
            ]
        )
        embed = Embed(
            title="Гра почалася, не кліпайте очима!",
            description="Світло тьмяніє...",
            color=Color.BLACK.value
        )
        embed.set_thumbnail(url="https://imgur.com/fBmiMNB.png")
        embed.add_field(name="Учасники:", value=player_list, inline=False)

        if round_logs:
            for round_field in round_logs:
                field_value = round_field.get("value") or "..."
                embed.add_field(name=round_field.get("name"), value=field_value,
                                inline=round_field.get("inline", False))

        return embed

    @staticmethod
    async def init_scp173_game_components(game_state: SCP173GameState) -> List[ActionRow]:
        mode_text = "До останнього" if game_state.mode == "last_man_standing" else "Звичайний"
        state_row = ActionRow(
            Button(
                style=ButtonStyle.secondary,
                label=f"Ставка: {game_state.bet} 💠",
                custom_id="game_scp173_bet_display",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=f"{len(game_state.players)}/{config.staring_max_players}",
                custom_id="game_scp173_count_display",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=f"Режим: {mode_text}",
                custom_id="game_scp173_mode_display",
                disabled=True
            )
        )
        return [state_row]

    @staticmethod
    async def format_scp173_single_winner_embed(winner: User, pot: int) -> Embed:
        embed = Embed(
            title="Єдиний виживший!",
            description=(
                f"{winner.mention} виходить з камери утримання неушкодженим\n\n"
                f"-# **Виграш:** {pot} 💠"
            ),
            color=Color.GREEN.value
        )
        embed.set_thumbnail(url="https://imgur.com/PJPoIes.png")
        return embed

    @staticmethod
    async def format_scp173_multiple_winners_embed(winners: List[User], winnings_per_player: int) -> Embed:
        winner_mentions = ", ".join([w.mention for w in winners])
        embed = Embed(
            title="Переможці!",
            description=(
                f"Смерть вашого колеги дала вам шанс вижити\n\n"
                f"**Вижили:** {winner_mentions}\n\n"
                f"-# **Виграш кожного:** {winnings_per_player} 💠"
            ),
            color=Color.GREEN.value
        )
        embed.set_thumbnail(url="https://imgur.com/PJPoIes.png")

        return embed

    @staticmethod
    async def format_scp173_no_survivors_embed() -> Embed:
        embed = Embed(
            title="Ніхто не вижив",
            description="Скульптура перемогла",
            color=Color.RED.value
        )
        embed.set_thumbnail(url="https://imgur.com/fBmiMNB.png")
        return embed

    @staticmethod
    async def format_hole_lobby_embed(game_state: HoleGameState) -> Embed:
        embed = Embed(
            title="Аномальна рулетка",
            color=Color.WHITE.value
        )
        embed.set_thumbnail(url="https://imgur.com/vHlPfOR.png")

        embed.description = "Поточні ставки:\n"
        for i, bet in enumerate(game_state.bets):
            embed.description += (
                f"{i + 1}. {bet.player.mention} **{bet.amount}** 💠 на `{bet.choice}`\n"
            )

        embed.set_footer(text=f"Гра розпочнеться автоматично через {config.hole_game_duration} секунд")
        return embed

    @staticmethod
    async def format_hole_results_embed(
            winning_item: str, winners: List[Tuple[User, int, str]]
    ) -> Embed:
        embed = Embed(
            title="Діра повернула предмет",
            description=f"``{winning_item}``\n",
            color=Color.GREEN.value if winners else Color.RED.value
        )
        embed.set_thumbnail(url="https://imgur.com/vHlPfOR.png")

        if winners:
            winner_lines = []
            for i, (player, payout) in enumerate(winners):
                winner_lines.append(
                    f"{i + 1}. {player.mention} виграв **{payout}** 💠"
                )
            embed.add_field(name="Переможці:", value="\n".join(winner_lines), inline=False)
        else:
            embed.description += "\nДіра поглинула всі ставки"

        return embed

    @staticmethod
    async def format_achievements_embed(
            target_user: User, achievements: List[Achievement], offset: int = 0
    ) -> Embed:
        embed = Embed(
            title=f"Досягнення користувача {target_user.display_name}",
            color=Color.YELLOW.value
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)

        if not achievements:
            embed.description = "У цього користувача поки немає досягнень"
        else:
            description_lines = [
                f"{offset + i + 1}. **{ach.name}** {ach.icon} \n-# {ach.description}"
                for i, ach in enumerate(achievements)
            ]
            embed.description = "\n\n".join(description_lines)

        return embed

    @staticmethod
    async def format_achievement_stats_embed(
            stats: List[Tuple[Achievement, int]],
            total_players: int,
            offset: int = 0
    ) -> Embed:
        embed = Embed(
            title="Статистика досягнень на сервері",
            color=Color.ORANGE.value
        )

        description_lines = []
        for i, (ach, count) in enumerate(stats):
            percentage = (count / total_players) * 100
            description_lines.append(
                f"{offset + i + 1}. **{ach.name}** {ach.icon} \n"
                f"-# {ach.description} – {percentage:.1f}%"
            )

        embed.description = "\n\n".join(description_lines)

        return embed


ui_utils = UIUtils()
