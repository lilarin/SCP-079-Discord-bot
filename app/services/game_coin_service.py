import random

import disnake

from app.core.models import User
from app.services.economy_management_service import economy_management_service
from app.utils.response_utils import response_utils
from app.utils.ui_utils import ui_utils


class CoinFlipService:
    @staticmethod
    async def play_game(interaction: disnake.ApplicationCommandInteraction, bet: int):
        user_id = interaction.user.id
        db_user, _ = await User.get_or_create(user_id=user_id)

        if db_user.balance < bet:
            await response_utils.edit_response(
                interaction, "У вас недостатньо коштів для цієї ставки"
            )
            return

        is_win = random.choice([True, False])

        if is_win:
            await economy_management_service.update_user_balance(user_id, bet)
            embed = await ui_utils.format_coin_flip_win_embed(bet=bet)
        else:
            await economy_management_service.update_user_balance(user_id, -bet)
            embed = await ui_utils.format_coin_flip_loss_embed(bet=bet)

        await response_utils.send_response(interaction, embed=embed)


coin_flip_service = CoinFlipService()
