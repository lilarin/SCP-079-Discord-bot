import random
from typing import Tuple

import disnake

from app.config import config
from app.core.models import User
from app.services.economy_management_service import economy_management_service
from app.utils.response_utils import response_utils
from app.utils.ui_utils import ui_utils


class CandyGameService:
    @staticmethod
    def _parse_state_from_components(components: list[disnake.ui.ActionRow]) -> Tuple[int, int, int]:
        state_buttons = components[0].children

        bet_label = state_buttons[0].label
        bet = int(bet_label.split(':')[1].strip().split(' ')[0])

        state_id = state_buttons[2].custom_id
        parts = state_id.split('_')
        player_taken = int(parts[2])
        pre_taken = int(parts[3])

        return bet, pre_taken, player_taken

    @staticmethod
    async def start_game(interaction: disnake.ApplicationCommandInteraction, bet: int):
        user_id = interaction.user.id
        db_user, _ = await User.get_or_create(user_id=user_id)

        if db_user.balance < bet:
            await response_utils.edit_ephemeral_response(interaction, "У вас недостатньо коштів для цієї ставки")
            return

        await economy_management_service.update_user_balance(user_id, -bet)

        pre_taken_candies = random.choices([0, 1, 2], weights=config.candy_pre_taken_weights, k=1)[0]
        player_taken_candies = 0

        potential_win = bet
        current_multiplier = 1.0

        embed, components = await ui_utils.format_candy_game_embed(
            bet=bet,
            pre_taken_candies=pre_taken_candies,
            player_taken_candies=player_taken_candies,
            is_first_turn=True,
            potential_win=potential_win,
            current_multiplier=current_multiplier
        )
        await response_utils.edit_ephemeral_response(interaction, embed=embed, components=components)

    async def take_candy(self, interaction: disnake.MessageInteraction):
        bet, pre_taken, player_taken = self._parse_state_from_components(interaction.message.components)

        player_taken += 1
        total_candies_for_loss = pre_taken + player_taken

        if total_candies_for_loss >= 3:
            loss_embed = await ui_utils.format_candy_loss_embed(bet=bet)
            await response_utils.edit_response(interaction, embed=loss_embed, components=[])
            return

        current_multiplier = config.candy_win_multipliers.get(player_taken, 1.0)
        potential_win = int(bet * current_multiplier)

        embed, components = await ui_utils.format_candy_game_embed(
            bet=bet,
            pre_taken_candies=pre_taken,
            player_taken_candies=player_taken,
            potential_win=potential_win,
            current_multiplier=current_multiplier,
            swap_colors=bool(player_taken == 2)
        )
        await response_utils.edit_response(interaction, embed=embed, components=components)

    async def leave_game(self, interaction: disnake.MessageInteraction):
        user_id = interaction.user.id
        bet, pre_taken, player_taken = self._parse_state_from_components(interaction.message.components)

        multiplier = config.candy_win_multipliers.get(player_taken, 1.0)
        winnings = int(bet * multiplier)

        await economy_management_service.update_user_balance(user_id, winnings)

        win_embed = await ui_utils.format_candy_win_embed(winnings=winnings)
        await response_utils.edit_response(interaction, embed=win_embed)


candy_game_service = CandyGameService()
