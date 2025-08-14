import asyncio
import random

import disnake

from app.config import config
from app.core.schemas import HoleGameState, HolePlayerBet
from app.services.economy_management_service import economy_management_service
from app.utils.response_utils import response_utils
from app.utils.ui_utils import ui_utils


class HoleGameService:
    def __init__(self):
        self.games: dict[int, HoleGameState] = {}

    @staticmethod
    async def item_autocomplete(interaction: disnake.ApplicationCommandInteraction, user_input: str) -> list[str]:
        user_input = user_input.lower()
        return [
           name for name in config.hole_items.values()
           if user_input in name.lower()
       ][:25]

    def is_game_active(self, channel_id: int) -> bool:
        return channel_id in self.games

    async def join_game(self, interaction: disnake.ApplicationCommandInteraction, bet: int, choice: str):
        channel_id = interaction.channel.id
        player = interaction.author

        game_state = self.games[channel_id]

        if any(p_bet.player.id == player.id for p_bet in game_state.bets):
            await economy_management_service.update_user_balance(player.id, bet)
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

    async def create_game(self, interaction: disnake.ApplicationCommandInteraction, bet: int, choice: str):
        channel_id = interaction.channel.id
        player = interaction.author

        initial_bet = HolePlayerBet(player=player, amount=bet, choice=choice)
        game_state = HoleGameState(message=await interaction.original_response(), bets=[initial_bet])

        self.games[channel_id] = game_state

        lobby_embed = await ui_utils.format_hole_lobby_embed(game_state)
        await response_utils.send_response(interaction, embed=lobby_embed)

        asyncio.create_task(self._run_game_finalization(interaction.channel))

    async def _run_game_finalization(self, channel: disnake.TextChannel):
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
                await economy_management_service.update_user_balance(p_bet.player.id, payout)
                winners.append((p_bet.player, payout))

        result_embed = await ui_utils.format_hole_results_embed(
            winning_item=winning_item_name, winners=winners
        )
        await response_utils.send_new_message(channel=channel, embed=result_embed)


hole_game_service = HoleGameService()
