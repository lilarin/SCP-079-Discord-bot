import asyncio
import random

from disnake import ApplicationCommandInteraction

from app.services import achievement_handler_service, economy_management_service
from app.utils.response_utils import response_utils
from app.utils.ui_utils import ui_utils


class CoinFlipService:
    @staticmethod
    async def play_game(interaction: ApplicationCommandInteraction, bet: int):
        is_win = random.choice([True, False])

        if is_win:
            winnings = bet * 2
            await economy_management_service.update_user_balance(
                interaction.user, winnings, f"Перемога у грі `{interaction.data.name}`"
            )
            embed = await ui_utils.format_coin_flip_win_embed(bet=winnings)
            asyncio.create_task(achievement_handler_service.handle_coin_flip_achievements(interaction.user, winnings))
        else:
            embed = await ui_utils.format_coin_flip_loss_embed(bet=bet)

        await response_utils.send_response(interaction, embed=embed)


coin_flip_service = CoinFlipService()
