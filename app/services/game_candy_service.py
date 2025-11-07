import asyncio
import random

from disnake import ui, ApplicationCommandInteraction, MessageInteraction

from app.core.variables import variables
from app.embeds import games_embeds
from app.localization import t
from app.services import achievement_handler_service, economy_management_service
from app.utils.response_utils import response_utils
from app.views.games_views import CandyGameView


class CandyGameService:
    @staticmethod
    def _parse_state_from_components(components: list[ui.ActionRow]) -> tuple[int, int, int]:
        state_id = components[0].children[2].custom_id
        parts = state_id.split("_")
        bet_label = components[0].children[0].label
        bet = int(bet_label.split(":")[1].strip().split(" ")[0])
        player_taken = int(parts[2])
        pre_taken = int(parts[3])
        return bet, pre_taken, player_taken

    @staticmethod
    async def start_game(interaction: ApplicationCommandInteraction, bet: int):
        pre_taken = random.choices([0, 1, 2], weights=variables.candy_pre_taken_weights, k=1)[0]

        embed = await games_embeds.format_candy_game_embed()
        view = CandyGameView(
            bet=bet,
            pre_taken=pre_taken,
            player_taken=0,
            potential_win=bet,
            multiplier=1.0,
            is_first_turn=True
        )
        await response_utils.send_response(interaction, embed=embed, view=view)

    async def take_candy(self, interaction: MessageInteraction):
        bet, pre_taken, player_taken = self._parse_state_from_components(interaction.message.components)
        player_taken += 1

        if pre_taken + player_taken >= 3:
            loss_embed = await games_embeds.format_candy_loss_embed(bet=bet)
            await response_utils.edit_response(interaction, embed=loss_embed, view=None)
            asyncio.create_task(
                achievement_handler_service.handle_candy_achievements(
                    interaction.user, player_taken, is_loss=True
                )
            )
            return

        multiplier = variables.candy_win_multipliers.get(player_taken, 1.0)
        potential_win = int(bet * multiplier)
        embed = await games_embeds.format_candy_game_embed()
        view = CandyGameView(
            bet=bet,
            pre_taken=pre_taken,
            player_taken=player_taken,
            potential_win=potential_win,
            multiplier=multiplier,
            is_first_turn=False
        )
        await response_utils.edit_response(interaction, embed=embed, view=view)

    async def leave_game(self, interaction: MessageInteraction):
        bet, _, player_taken = self._parse_state_from_components(interaction.message.components)
        multiplier = variables.candy_win_multipliers.get(player_taken, 1.0)
        winnings = int(bet * multiplier)

        await economy_management_service.update_user_balance(
            interaction.user, winnings, t("economy.reasons.game_win_candy")
        )
        win_embed = await games_embeds.format_candy_win_embed(winnings=winnings)
        await response_utils.edit_response(interaction, embed=win_embed, view=None)

        asyncio.create_task(
            achievement_handler_service.handle_candy_achievements(interaction.user, player_taken, is_loss=False)
        )


candy_game_service = CandyGameService()
