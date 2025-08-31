import asyncio
import random

from disnake import ApplicationCommandInteraction, TextChannel

from app.config import config
from app.core.schemas import HoleGameState, HolePlayerBet
from app.services import achievement_handler_service, economy_management_service
from app.utils.response_utils import response_utils
from app.utils.ui_utils import ui_utils


class HoleGameService:
    def __init__(self):
        self.games: dict[int, HoleGameState] = {}

    @staticmethod
    async def item_autocomplete(interaction: ApplicationCommandInteraction, user_input: str) -> list[str]:
        user_input = user_input.lower()
        return [
           name for name in config.hole_items.values()
           if user_input in name.lower()
       ][:25]

    def is_game_active(self, channel_id: int) -> bool:
        return channel_id in self.games

    async def join_game(self, interaction: ApplicationCommandInteraction, bet: int, choice: str):
        channel_id = interaction.channel.id
        player = interaction.user

        game_state = self.games[channel_id]

        if any(p_bet.player.id == player.id for p_bet in game_state.bets):
            await economy_management_service.update_user_balance(
                player, bet, "Повернення повторної ставки у активній грі `діра`"
            )
            await response_utils.send_response(
                interaction, "Ви вже зробили ставку в активній гру", delete_after=5
            )
            return

        await response_utils.send_response(
            interaction, message=f"{player.mention} приєднався до гри", delete_after=5
        )

        game_state.bets.append(
            HolePlayerBet(player=player, amount=bet, choice=choice)
        )

        lobby_embed = await ui_utils.format_hole_lobby_embed(game_state)

        await response_utils.edit_message(game_state.message, embed=lobby_embed)

    async def create_game(self, interaction: ApplicationCommandInteraction, bet: int, choice: str):
        channel_id = interaction.channel.id
        player = interaction.user

        initial_bet = HolePlayerBet(player=player, amount=bet, choice=choice)
        game_state = HoleGameState(message=await interaction.original_response(), bets=[initial_bet])

        self.games[channel_id] = game_state

        lobby_embed = await ui_utils.format_hole_lobby_embed(game_state)
        await response_utils.send_response(interaction, embed=lobby_embed)

        asyncio.create_task(self._run_game_finalization(interaction.channel))

    async def _run_game_finalization(self, channel: TextChannel):
        channel_id = channel.id
        await asyncio.sleep(config.hole_game_duration)

        if channel_id not in self.games:
            return

        game_state_to_process = self.games.pop(channel_id)

        winning_number = random.randint(0, 36)
        winning_item_name = config.hole_items[winning_number]
        winners = []
        for p_bet in game_state_to_process.bets:
            bet_option = config.hole_bet_options[p_bet.choice]
            if winning_number in bet_option["numbers"]:
                payout = p_bet.amount * bet_option["multiplier"]
                await economy_management_service.update_user_balance(
                    p_bet.player, payout, "Перемога у грі `діра`"
                )
                winners.append((p_bet.player, payout))

                is_jackpot = bet_option["multiplier"] == 36
                is_o5_win = winning_number == 0

                asyncio.create_task(achievement_handler_service.handle_hole_achievements(
                    p_bet.player, is_jackpot, is_o5_win, payout
                ))

        result_embed = await ui_utils.format_hole_results_embed(
            winning_item=winning_item_name, winners=winners
        )
        await response_utils.send_new_message(channel=channel, embed=result_embed)


hole_game_service = HoleGameService()
