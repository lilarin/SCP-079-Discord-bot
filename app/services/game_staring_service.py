import asyncio
import random
from typing import Dict

from disnake import ApplicationCommandInteraction, MessageInteraction, TextChannel, User

from app.core.models import User as UserModel
from app.core.schemas import SCP173GameState
from app.core.variables import variables
from app.embeds import games_embeds
from app.localization import t
from app.services import achievement_handler_service, economy_management_service
from app.utils.response_utils import response_utils
from app.views.games_views import StaringGameLobbyView, StaringGameInfoView


class StaringGameService:
    def __init__(self):
        self.games: Dict[int, SCP173GameState] = {}

    async def start_lobby(self, interaction: ApplicationCommandInteraction, bet: int, mode: str) -> None:
        host = interaction.user
        game_state = SCP173GameState(
            host=host, bet=bet, mode=mode, players=[host], channel_id=interaction.channel_id
        )
        embed = await games_embeds.format_scp173_lobby_embed(game_state)
        view = StaringGameLobbyView(game_state)
        await response_utils.send_response(interaction, embed=embed, view=view)
        message = await interaction.original_message()
        game_state.message_id = message.id
        self.games[message.id] = game_state

        await asyncio.sleep(variables.staring_lobby_duration)
        if message.id in self.games and not self.games[message.id].is_started:
            await self._auto_start_or_cancel(interaction, message.id)

    async def _auto_start_or_cancel(self, interaction: ApplicationCommandInteraction, message_id: int):
        current_state = self.games[message_id]
        if len(current_state.players) < 2:
            await economy_management_service.update_user_balance(
                current_state.host,
                current_state.bet,
                t("economy.reasons.staring_game_not_enough_players_refund"),
                balance_only=True
            )
            message_to_edit = await interaction.original_message()
            await response_utils.edit_message(
                message_to_edit,
                content=t("responses.games.staring.game_cancelled_not_enough_players"),
                embed=None, view=None
            )
            del self.games[message_id]
        else:
            await self.run_game(interaction.channel, message_id)

    async def handle_join(self, interaction: MessageInteraction) -> None:
        message_id = interaction.message.id
        if message_id not in self.games or self.games[message_id].is_started:
            return await response_utils.send_ephemeral_response(
                interaction, t("responses.games.staring.game_ended_or_started")
            )

        game_state = self.games[message_id]
        user = interaction.user
        if user in game_state.players:
            return await response_utils.send_ephemeral_response(
                interaction, t("responses.games.staring.already_in_game")
            )
        if len(game_state.players) >= variables.staring_max_players:
            return await response_utils.send_ephemeral_response(
                interaction, t("responses.games.staring.lobby_full")
            )

        db_user, _ = await UserModel.get_or_create(user_id=user.id)
        if db_user.balance < game_state.bet:
            return await response_utils.send_ephemeral_response(
                interaction, t("errors.insufficient_funds_for_bet_simple")
            )

        await economy_management_service.update_user_balance(
            user,
            -game_state.bet,
            t("economy.reasons.staring_game_bet"),
            balance_only=True
        )
        game_state.players.append(user)

        embed = await games_embeds.format_scp173_lobby_embed(game_state)
        view = StaringGameLobbyView(game_state)
        await response_utils.edit_response(interaction, embed=embed, view=view)

        if len(game_state.players) == variables.staring_max_players:
            await self.run_game(interaction.channel, message_id)

    async def handle_start(self, interaction: MessageInteraction) -> None:
        message_id = interaction.message.id
        if message_id not in self.games or self.games[message_id].is_started:
            return await response_utils.send_ephemeral_response(
                interaction, t("responses.games.staring.game_ended_or_started")
            )

        game_state = self.games[message_id]
        if len(game_state.players) < 2:
            return await response_utils.send_ephemeral_response(
                interaction, t("responses.games.staring.need_2_players_to_start")
            )

        await self.run_game(interaction.channel, message_id)

    async def run_game(self, channel: TextChannel, message_id: int) -> None:
        if message_id not in self.games or self.games[message_id].is_started:
            return

        game_state = self.games[message_id]
        game_state.is_started = True
        message = await channel.fetch_message(message_id)

        start_embed = await games_embeds.format_scp173_start_game_embed(game_state)
        info_view = StaringGameInfoView(game_state)
        await response_utils.edit_message(message, embed=start_embed, view=info_view)

        asyncio.create_task(
            achievement_handler_service.handle_scp173_achievements(
                game_state.host,
                is_host=True,
                is_survivor=False,
                is_first_death=False
            )
        )
        await asyncio.sleep(3)

        survivors = list(game_state.players)
        total_players_at_start = len(survivors)
        round_number = 0
        round_fields = []

        while len(survivors) > 1:
            round_number += 1
            current_round_log = []
            round_field_name = t("ui.staring_game.round_title", round_number=round_number)
            round_fields.append({"name": round_field_name, "value": "...", "inline": False})

            embed_in_progress = await games_embeds.format_scp173_start_game_embed(
                game_state, round_logs=round_fields
            )
            await response_utils.edit_message(message, embed=embed_in_progress, view=info_view)
            await asyncio.sleep(2)

            random.shuffle(survivors)
            current_round_survivors = []
            a_death_occurred = False
            death_chance = 1.0 / max(variables.staring_max_players - (round_number - 1), 1)

            for player in survivors:
                await asyncio.sleep(2)
                if random.random() < death_chance:
                    a_death_occurred = True
                    current_round_log.append(
                        t("responses.games.staring.round_log_death", player_mention=player.mention))
                    if round_number == 1:
                        asyncio.create_task(
                            achievement_handler_service.handle_scp173_achievements(
                                player,
                                is_host=False,
                                is_survivor=False,
                                is_first_death=True
                            )
                        )
                else:
                    current_round_log.append(
                        t("responses.games.staring.round_log_survived", player_mention=player.mention))
                    current_round_survivors.append(player)

                round_fields[-1]["value"] = "\n".join(current_round_log)
                embed_in_progress = await games_embeds.format_scp173_start_game_embed(
                    game_state, round_logs=round_fields
                )
                await response_utils.edit_message(message, embed=embed_in_progress, view=info_view)

            survivors = current_round_survivors

            if game_state.mode == "normal" and a_death_occurred:
                await self._end_game_normal_mode(channel, survivors, game_state.bet * total_players_at_start)
                if message_id in self.games:
                    del self.games[message_id]
                return

            if len(survivors) <= 1:
                break

            summary_key = "round_summary_no_death" if not a_death_occurred else "round_summary_death"
            current_round_log.append(t(f"responses.games.staring.{summary_key}"))
            round_fields[-1]["value"] = "\n".join(current_round_log)
            embed_in_progress = await games_embeds.format_scp173_start_game_embed(
                game_state, round_logs=round_fields
            )
            await response_utils.edit_message(message, embed=embed_in_progress, view=info_view)
            await asyncio.sleep(3)

        await self._end_game_last_man_standing(channel, survivors, game_state.bet * total_players_at_start)
        if message_id in self.games:
            del self.games[message_id]

    async def _end_game_normal_mode(self, channel: TextChannel, survivors: list, pot: int):
        if not survivors:
            embed = await games_embeds.format_scp173_no_survivors_embed()
            await response_utils.send_new_message(channel, embed=embed)
        elif len(survivors) == 1:
            await self._handle_single_winner(channel, survivors[0], pot)
        else:
            winnings_per_player = pot // len(survivors)
            for winner in survivors:
                await economy_management_service.update_user_balance(
                    winner,
                    winnings_per_player,
                    t("economy.reasons.game_win_staring"),
                    balance_only=True
                )
                asyncio.create_task(
                    achievement_handler_service.handle_scp173_achievements(
                        winner,
                        is_host=False,
                        is_survivor=True,
                        is_first_death=False,
                        pot=winnings_per_player
                    )
                )
            embed = await games_embeds.format_scp173_multiple_winners_embed(survivors, winnings_per_player)
            await response_utils.send_new_message(channel, embed=embed)

    async def _end_game_last_man_standing(self, channel: TextChannel, survivors: list, pot: int):
        if len(survivors) == 1:
            await self._handle_single_winner(channel, survivors[0], pot)
        else:
            embed = await games_embeds.format_scp173_no_survivors_embed()
            await response_utils.send_new_message(channel, embed=embed)

    @staticmethod
    async def _handle_single_winner(channel: TextChannel, winner: User, pot: int):
        await economy_management_service.update_user_balance(
            winner,
            pot,
            t("economy.reasons.game_win_staring"),
            balance_only=True
        )
        asyncio.create_task(
            achievement_handler_service.handle_scp173_achievements(
                winner,
                is_host=False,
                is_survivor=True,
                is_first_death=False,
                pot=pot
            )
        )
        embed = await games_embeds.format_scp173_single_winner_embed(winner, pot)
        await response_utils.send_new_message(channel, embed=embed)


staring_game_service = StaringGameService()
