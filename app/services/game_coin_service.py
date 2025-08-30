import random

import disnake

from app.services.economy_management_service import economy_management_service
from app.utils.response_utils import response_utils
from app.utils.ui_utils import ui_utils


class CoinFlipService:
    @staticmethod
    async def play_game(interaction: disnake.ApplicationCommandInteraction, bet: int):
        is_win = random.choice([True, False])

        if is_win:
            await economy_management_service.update_user_balance(
                interaction.user, bet * 2, f"Перемога у грі `{interaction.data.name}`"
            )
            embed = await ui_utils.format_coin_flip_win_embed(bet=bet * 2)
        else:
            embed = await ui_utils.format_coin_flip_loss_embed(bet=bet)

        await response_utils.send_response(interaction, embed=embed)


coin_flip_service = CoinFlipService()
