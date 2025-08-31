import asyncio
from typing import List, Tuple, Optional

from disnake import Embed, File, Role, ButtonStyle, User, Member, Guild
from disnake.ext.commands import InteractionBot
from disnake.ui import ActionRow, Button

from app.config import config
from app.core.enums import Color
from app.core.models import SCPObject, Item, Achievement
from app.core.schemas import SCP173GameState, HoleGameState
from app.localization import t


class UIUtils:
    @staticmethod
    async def format_leaderboard_embed(
            bot: InteractionBot,
            guild: Guild,
            top_users: List[Tuple[int, int]],
            top_criteria: str,
            hint: str,
            symbol: str,
            color: int,
            offset: int = 0
    ) -> Embed:
        embed = Embed(
            title=t("ui.leaderboard.title", top_criteria=top_criteria),
            color=color,
        )

        if not top_users:
            embed.description = t("ui.leaderboard.no_users")
            embed.description += f"\n-# {hint}"
            return embed

        user_ids = [user_id for user_id, _ in top_users]

        fetched_members: List[Member] = await guild.get_or_fetch_members(user_ids)
        fetched_member_ids = {member.id for member in fetched_members}

        missing_user_ids = [user_id for user_id in user_ids if user_id not in fetched_member_ids]

        fallback_users: List[User] = []
        if missing_user_ids:
            user_fetch_tasks = [bot.get_or_fetch_user(user_id) for user_id in missing_user_ids]
            fallback_users = await asyncio.gather(*user_fetch_tasks)

        all_fetched_users = {user.id: user for user in fetched_members + fallback_users if user}

        description_lines = []
        for i, (user_id, count) in enumerate(top_users, 1):
            user = all_fetched_users.get(user_id)
            if user:
                description_lines.append(
                    f"{i + offset}. {user.mention} (`{user.name}`) – **{count} {symbol}**"
                )

        if description_lines:
            embed.description = "\n".join(description_lines)
        else:
            embed.description = t("ui.leaderboard.fetch_error")

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
            ),
        ]

        return ActionRow(*buttons) if not all(button.disabled for button in buttons) else None

    @staticmethod
    async def format_new_user_embed(user_mention: str, card: File, color: int) -> Embed:
        embed = Embed(
            description=t("ui.new_user_welcome", user_mention=user_mention),
            color=color
        )
        embed.set_image(file=card)

        return embed

    @staticmethod
    async def format_user_embed(
            card: File,
            color: int,
            achievements_count: int,
            dossier: Optional[str] = None,
            role: Optional[Role] = None,
    ) -> Embed:
        embed = Embed(
            title=t("ui.user_card.title"),
            color=color
        )
        embed.set_image(file=card)

        if role:
            embed.add_field(name=t("ui.user_card.role_field"), value=role.mention, inline=False)

        if achievements_count > 0:
            embed.add_field(
                name=t("ui.user_card.achievements_field"),
                value=f"{achievements_count} / {len(config.achievements)}",
                inline=False,
            )

        if dossier:
            embed.add_field(name=t("ui.user_card.dossier_field"), value=dossier, inline=False)

        return embed

    @staticmethod
    async def format_article_embed(article: SCPObject, image_file: File) -> Tuple[Embed, ActionRow]:
        embed = Embed(color=int(config.scp_class_config[article.object_class][0].lstrip("#"), 16))
        name_confirm = Button(
            style=ButtonStyle.link,
            url=article.link,
            label=t("ui.article.view_button"),
            emoji=config.scp_class_config[article.object_class][1],
        )

        embed.set_image(file=image_file)
        return embed, ActionRow(name_confirm)

    @staticmethod
    async def format_balance_embed(user_avatar_url: User, balance: int, reputation: int, position: int) -> Embed:
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

    @staticmethod
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

            card_config = config.cards.get(item.item_id)

            if card_config and card_config.required_achievements:
                required_ach = []
                for ach_id in card_config.required_achievements:
                    ach_config = config.achievements.get(ach_id)
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

    @staticmethod
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

    @staticmethod
    async def format_legal_work_embed(prompt: str, reward: int) -> Embed:
        return Embed(
            title=t("ui.work.legal_title"),
            description=f'{prompt}\n\n-# {t("ui.work.earned", amount=reward)}',
            color=Color.GREEN.value
        )

    @staticmethod
    async def format_non_legal_work_embed(prompt: str, amount: int, is_success: bool) -> Embed:
        if is_success:
            title = t("ui.work.risky_title")
            description = f'{prompt}\n\n-# {t("ui.work.earned", amount=amount)}'
            color = Color.GREEN.value
        else:
            title = t("ui.work.risky_title")
            description = f'{prompt}\n\n-# {t("ui.work.lost", amount=amount)}'
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
            title=t("ui.crystallize.title"),
            description=t("ui.crystallize.description"),
            color=Color.LIGHT_PINK.value
        )
        embed.set_thumbnail(url="https://imgur.com/DOAsTfy.png")

        buttons = [
            Button(
                style=ButtonStyle.secondary,
                label=t("ui.crystallize.bet_button", bet=bet),
                custom_id="display_bet",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=t("ui.crystallize.multiplier_button", multiplier=f"{multiplier:.2f}"),
                custom_id="display_multiplier",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=t("ui.crystallize.loss_chance_button", loss_chance=f"{loss_chance:.1f}"),
                custom_id="display_loss",
                disabled=True
            )
        ]
        state_row = ActionRow(*buttons)

        continue_button = Button(
            style=ButtonStyle.primary,
            label=t("ui.crystallize.continue_button"),
            custom_id="game_crystallize_continue"
        )
        stop_button = Button(
            style=ButtonStyle.green,
            label=t("ui.crystallize.cash_out_button", potential_win=potential_win),
            custom_id="game_crystallize_stop",
            disabled=is_first_turn
        )
        action_row = ActionRow(continue_button, stop_button)

        return embed, [state_row, action_row]

    @staticmethod
    async def format_crystallize_win_embed(bet: int, winnings: int, multiplier: float) -> Embed:
        embed = Embed(
            title=t("ui.crystallize.win_title"),
            description=t(
                "ui.crystallize.win_description", bet=bet, multiplier=f"{multiplier:.2f}", winnings=winnings
            ),
            color=Color.GREEN.value
        )
        embed.set_thumbnail(url="https://imgur.com/DOAsTfy.png")
        return embed

    @staticmethod
    async def format_crystallize_loss_embed(bet: int) -> Embed:
        embed = Embed(
            title=t("ui.crystallize.loss_title"),
            description=t("ui.crystallize.loss_description", bet=bet),
            color=Color.RED.value
        )
        embed.set_thumbnail(url="https://imgur.com/DOAsTfy.png")
        return embed

    @staticmethod
    async def format_coin_flip_win_embed(bet: int) -> Embed:
        embed = Embed(
            title=t("ui.coin_flip.win_title"),
            description=t("ui.coin_flip.win_description", bet=bet),
            color=Color.GREEN.value
        )
        embed.set_thumbnail(url="https://imgur.com/n4znTOU.png")
        return embed

    @staticmethod
    async def format_coin_flip_loss_embed(bet: int) -> Embed:
        embed = Embed(
            title=t("ui.coin_flip.loss_title"),
            description=t("ui.coin_flip.loss_description", bet=bet),
            color=Color.RED.value
        )
        embed.set_thumbnail(url="https://imgur.com/n4znTOU.png")
        return embed

    @staticmethod
    async def format_candy_game_embed(
            bet: int,
            pre_taken_candies: int,
            player_taken_candies: int,
            potential_win: int,
            current_multiplier: float,
            swap_colors: bool = False,
            is_first_turn: bool = False
    ) -> Tuple[Embed, List[ActionRow]]:
        embed = Embed(
            title=t("ui.candy_game.title"),
            description=t("ui.candy_game.description"),
            color=Color.ORANGE.value
        )
        embed.set_thumbnail(url="https://imgur.com/mGBlbYS.png")

        state_buttons = [
            Button(
                style=ButtonStyle.secondary,
                label=t("ui.candy_game.bet_button", bet=bet),
                custom_id="candy_display_bet",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=t("ui.candy_game.multiplier_button", multiplier=f"{current_multiplier:.1f}"),
                custom_id="candy_display_multiplier",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=t("ui.candy_game.taken_button", count=player_taken_candies),
                custom_id=f"candy_state_{player_taken_candies}_{pre_taken_candies}",
                disabled=True
            )
        ]
        state_row = ActionRow(*state_buttons)

        take_button_color, leave_button_color = (
            ButtonStyle.primary, ButtonStyle.green
        ) if not swap_colors else (
            ButtonStyle.green, ButtonStyle.primary
        )

        take_button = Button(
            style=take_button_color,
            label=t("ui.candy_game.take_button"),
            custom_id="game_candy_take"
        )
        leave_button = Button(
            style=leave_button_color,
            label=t("ui.candy_game.leave_button", potential_win=potential_win),
            custom_id="game_candy_leave",
            disabled=is_first_turn
        )
        action_row = ActionRow(take_button, leave_button)

        return embed, [state_row, action_row]

    @staticmethod
    async def format_candy_win_embed(winnings: int) -> Embed:
        embed = Embed(
            title=t("ui.candy_game.win_title"),
            description=t("ui.candy_game.win_description", winnings=winnings),
            color=Color.GREEN.value
        )
        embed.set_thumbnail(url="https://imgur.com/mGBlbYS.png")
        return embed

    @staticmethod
    async def format_candy_loss_embed(bet: int) -> Embed:
        embed = Embed(
            title=t("ui.candy_game.loss_title"),
            description=t("ui.candy_game.loss_description", bet=bet),
            color=Color.RED.value
        )
        embed.set_thumbnail(url="https://imgur.com/mGBlbYS.png")
        return embed

    @staticmethod
    async def format_coguard_embed(
            bet: int,
            multiplier: float,
            potential_win: int,
            current_number: int,
            win_streak: int,
            is_first_turn: bool = False
    ) -> Tuple[Embed, List[ActionRow]]:
        embed = Embed(
            title=t("ui.coguard_game.title"),
            description=t("ui.coguard_game.description", current_number=current_number),
            color=Color.BLUE.value
        )
        embed.set_thumbnail(url="https://imgur.com/pAW9s4O.png")
        state_buttons = [
            Button(
                style=ButtonStyle.secondary,
                label=t("ui.coguard_game.bet_button", bet=bet),
                custom_id="coguard_display_bet",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=t("ui.coguard_game.multiplier_button", multiplier=f"{multiplier:.2f}"),
                custom_id="coguard_display_multiplier",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=t("ui.coguard_game.number_button", number=current_number),
                custom_id="coguard_display_number",
                disabled=True
            ),
            Button(
                style=ButtonStyle.secondary,
                label=t("ui.coguard_game.streak_button", streak=win_streak),
                custom_id="coguard_display_streak",
                disabled=True
            )
        ]
        state_row = ActionRow(*state_buttons)

        higher_button = Button(
            style=ButtonStyle.primary,
            label=t("ui.coguard_game.higher_button"),
            emoji="⬆️",
            custom_id="game_coguard_higher"
        )
        lower_button = Button(
            style=ButtonStyle.primary,
            label=t("ui.coguard_game.lower_button"),
            emoji="⬇️",
            custom_id="game_coguard_lower"
        )
        cashout_button = Button(
            style=ButtonStyle.green,
            label=t("ui.coguard_game.cash_out_button", potential_win=potential_win),
            custom_id="game_coguard_cashout",
            disabled=is_first_turn
        )
        action_row = ActionRow(higher_button, lower_button, cashout_button)

        return embed, [state_row, action_row]

    @staticmethod
    async def format_coguard_win_embed(bet: int, winnings: int, multiplier: float, win_streak: int) -> Embed:
        embed = Embed(
            title=t("ui.coguard_game.win_title"),
            description=t(
                "ui.coguard_game.win_description",
                bet=bet,
                win_streak=win_streak,
                multiplier=f"{multiplier:.2f}",
                winnings=winnings
            ),
            color=Color.GREEN.value
        )
        embed.set_thumbnail(url="https://imgur.com/pAW9s4O.png")
        return embed

    @staticmethod
    async def format_coguard_loss_embed(bet: int, win_streak: int) -> Embed:
        embed = Embed(
            title=t("ui.coguard_game.loss_title"),
            description=t("ui.coguard_game.loss_description", win_streak=win_streak, bet=bet),
            color=Color.RED.value
        )
        embed.set_thumbnail(url="https://imgur.com/pAW9s4O.png")
        return embed

    @staticmethod
    async def format_scp173_lobby_embed(game_state: SCP173GameState) -> Embed:
        embed = Embed(
            title=t("ui.staring_game.title"),
            description=t("ui.staring_game.lobby_description"),
            color=Color.WHITE.value
        )
        embed.set_thumbnail(url="https://imgur.com/PJPoIes.png")

        player_list = "\n".join(
            [f"{i + 1}. {player.mention}" for i, player in enumerate(list(game_state.players))]
        )
        embed.add_field(
            name=t("ui.staring_game.players_field"),
            value=player_list if player_list else t("ui.staring_game.no_players"),
            inline=False
        )
        embed.set_footer(text=t("ui.staring_game.lobby_footer", duration=config.staring_lobby_duration))
        return embed

    async def init_scp173_lobby_components(self, game_state: SCP173GameState) -> List[ActionRow]:
        is_full = len(game_state.players) >= config.staring_max_players
        state_row = await self.init_scp173_game_components(game_state)

        action_row = ActionRow(
            Button(
                style=ButtonStyle.green,
                label=t("ui.staring_game.join_button"),
                custom_id="game_scp173_join",
                disabled=is_full
            ),
            Button(
                style=ButtonStyle.primary,
                label=t("ui.staring_game.start_button"),
                custom_id="game_scp173_start"
            )
        )

        return [state_row[0], action_row]

    @staticmethod
    async def format_scp173_start_game_embed(
            game_state: SCP173GameState, round_logs: Optional[List[dict]] = None
    ) -> Embed:
        player_list = "\n".join(
            [f"{i + 1}. {player.mention}" for i, player in enumerate(list(game_state.players))]
        )
        embed = Embed(
            title=t("ui.staring_game.game_start_title"),
            description=t("ui.staring_game.game_start_description"),
            color=Color.BLACK.value
        )
        embed.set_thumbnail(url="https://imgur.com/fBmiMNB.png")
        embed.add_field(name=t("ui.staring_game.players_field"), value=player_list, inline=False)

        if round_logs:
            for round_field in round_logs:
                field_value = round_field.get("value") or "..."
                embed.add_field(
                    name=round_field.get("name"),
                    value=field_value,
                    inline=round_field.get("inline", False),
                )

        return embed

    @staticmethod
    async def init_scp173_game_components(game_state: SCP173GameState) -> List[ActionRow]:
        mode_text = (
            t("ui.staring_game.mode_lms")
            if game_state.mode == "last_man_standing"
            else t("ui.staring_game.mode_normal")
        )
        state_row = ActionRow(
            Button(
                style=ButtonStyle.secondary,
                label=t("ui.staring_game.bet_button", bet=game_state.bet),
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
                label=t("ui.staring_game.mode_button", mode=mode_text),
                custom_id="game_scp173_mode_display",
                disabled=True
            )
        )
        return [state_row]

    @staticmethod
    async def format_scp173_single_winner_embed(winner: User, pot: int) -> Embed:
        embed = Embed(
            title=t("ui.staring_game.single_winner_title"),
            description=t("ui.staring_game.single_winner_description", winner_mention=winner.mention, pot=pot),
            color=Color.GREEN.value
        )
        embed.set_thumbnail(url="https://imgur.com/PJPoIes.png")
        return embed

    @staticmethod
    async def format_scp173_multiple_winners_embed(winners: List[User], winnings_per_player: int) -> Embed:
        winner_mentions = ", ".join([w.mention for w in winners])
        embed = Embed(
            title=t("ui.staring_game.multi_winner_title"),
            description=t(
                "ui.staring_game.multi_winner_description",
                winner_mentions=winner_mentions,
                winnings=winnings_per_player
            ),
            color=Color.GREEN.value
        )
        embed.set_thumbnail(url="https://imgur.com/PJPoIes.png")

        return embed

    @staticmethod
    async def format_scp173_no_survivors_embed() -> Embed:
        embed = Embed(
            title=t("ui.staring_game.no_survivors_title"),
            description=t("ui.staring_game.no_survivors_description"),
            color=Color.RED.value
        )
        embed.set_thumbnail(url="https://imgur.com/fBmiMNB.png")
        return embed

    @staticmethod
    async def format_hole_lobby_embed(game_state: HoleGameState) -> Embed:
        embed = Embed(
            title=t("ui.hole_game.title"),
            color=Color.WHITE.value
        )
        embed.set_thumbnail(url="https://imgur.com/vHlPfOR.png")

        embed.description = t("ui.hole_game.current_bets")
        for i, bet in enumerate(game_state.bets):
            embed.description += f"{i + 1}. {bet.player.mention} **{bet.amount}** 💠 на `{bet.choice}`\n"

        embed.set_footer(text=t("ui.hole_game.lobby_footer", duration=config.hole_game_duration))
        return embed

    @staticmethod
    async def format_hole_results_embed(
            winning_item: str, winners: List[Tuple[User, int, str]]
    ) -> Embed:
        embed = Embed(
            title=t("ui.hole_game.result_title"),
            description=f"``{winning_item}``\n",
            color=Color.GREEN.value if winners else Color.RED.value
        )
        embed.set_thumbnail(url="https://imgur.com/vHlPfOR.png")

        if winners:
            winner_lines = []
            for i, (player, payout) in enumerate(winners):
                winner_lines.append(f"{i + 1}. {player.mention} виграв **{payout}** 💠")
            embed.add_field(name=t("ui.hole_game.winners_field"), value="\n".join(winner_lines), inline=False)
        else:
            embed.description += t("ui.hole_game.no_winners")

        return embed

    @staticmethod
    async def format_achievements_embed(
            target_user: User | Member, achievements: List[Achievement], offset: int = 0
    ) -> Embed:
        embed = Embed(
            title=t("ui.achievements.user_title", user_name=target_user.display_name),
            color=Color.YELLOW.value
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)

        if not achievements:
            embed.description = t("ui.achievements.no_achievements")
        else:
            description_lines = [
                f"{offset + i + 1}. **{ach.name}** {ach.icon} \n-# {ach.description}"
                for i, ach in enumerate(achievements)
            ]
            embed.description = "\n\n".join(description_lines)

        return embed

    @staticmethod
    async def format_achievement_stats_embed(
            stats: List[Tuple[Achievement, int]], total_players: int, offset: int = 0
    ) -> Embed:
        embed = Embed(
            title=t("ui.achievements.stats_title"),
            color=Color.ORANGE.value
        )

        description_lines = []
        for i, (ach, count) in enumerate(stats):
            percentage = (count / total_players) * 100 if total_players > 0 else 0
            description_lines.append(
                f"{offset + i + 1}. **{ach.name}** {ach.icon} ({percentage:.1f}%)\n"
                f"-# {ach.description}"
            )

        embed.description = "\n\n".join(description_lines)

        return embed

    @staticmethod
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

    @staticmethod
    async def format_games_info_embed() -> Embed:
        embed = Embed(
            title=t("ui.games_info.title"),
            description=t("ui.games_info.description"),
            color=Color.WHITE.value
        )
        embed.set_image(url="https://imgur.com/dzOcnnY.png")

        embed.add_field(
            name=t("ui.games_info.crystallization_name"),
            value=t("ui.games_info.crystallization_desc"),
            inline=False
        )
        embed.add_field(
            name=t("ui.games_info.coin_name"),
            value=t("ui.games_info.coin_desc"),
            inline=False
        )
        embed.add_field(
            name=t("ui.games_info.candy_name"),
            value=t("ui.games_info.candy_desc"),
            inline=False
        )
        embed.add_field(
            name=t("ui.games_info.coguard_name"),
            value=t("ui.games_info.coguard_desc"),
            inline=False
        )
        embed.add_field(
            name=t("ui.games_info.staring_name"),
            value=t("ui.games_info.staring_desc"),
            inline=False
        )
        embed.add_field(
            name=t("ui.games_info.hole_name"),
            value=t("ui.games_info.hole_desc"),
            inline=False
        )

        return embed


ui_utils = UIUtils()
