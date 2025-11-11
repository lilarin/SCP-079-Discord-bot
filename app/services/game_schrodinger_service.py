import asyncio
import random
from typing import Dict

from disnake import ApplicationCommandInteraction, MessageInteraction, Message

from app.core.schemas import SchrodingerGameState
from app.core.variables import variables
from app.embeds import games_embeds
from app.localization import t
from app.services import economy_management_service
from app.utils.response_utils import response_utils
from app.views.games_views import SchrodingerView


class SchrodingerGameService:
    def __init__(self):
        self.games: Dict[int, SchrodingerGameState] = {}

    async def _cleanup_game(self, message: Message):
        await asyncio.sleep(180)
        if message.id in self.games:
            del self.games[message.id]
            await response_utils.edit_message(
                message, content=t("responses.games.game_timed_out")
            )

    async def start_game(self, interaction: ApplicationCommandInteraction, bet: int):
        num_containers = random.randint(3, 5)
        containers = ["anomaly"] + ["empty"] * (num_containers - 1)
        random.shuffle(containers)
        winning_container_index = containers.index("anomaly")

        game_state = SchrodingerGameState(
            bet=bet,
            num_containers=num_containers,
            winning_container_index=winning_container_index
        )

        embed = await games_embeds.format_schrodinger_initial_choice_embed(num_containers)
        view = SchrodingerView(game_state=game_state)
        await response_utils.send_response(interaction, embed=embed, view=view)

        message = await interaction.original_message()
        self.games[message.id] = game_state
        asyncio.create_task(self._cleanup_game(message))

    async def handle_initial_choice(self, interaction: MessageInteraction):
        game_state = self.games.get(interaction.message.id)
        if not game_state or game_state.player_initial_choice_index is not None:
            return

        player_choice_index = int(interaction.component.custom_id.split('_')[-1])
        game_state.player_initial_choice_index = player_choice_index

        empty_indices = [
            i for i in range(game_state.num_containers)
            if i != game_state.winning_container_index and i != player_choice_index
        ]

        revealed_container_index = random.choice(empty_indices)
        game_state.revealed_container_indices = [revealed_container_index]

        view = SchrodingerView(game_state=game_state, phase=2)

        current_embed = interaction.message.embeds[0]
        await response_utils.edit_response(interaction, embed=current_embed, view=view)

    async def handle_final_choice(self, interaction: MessageInteraction):
        game_state = self.games.get(interaction.message.id)
        if not game_state:
            return

        final_choice_index = int(interaction.component.custom_id.split('_')[-1])
        was_switched = (final_choice_index != game_state.player_initial_choice_index)

        is_win = (final_choice_index == game_state.winning_container_index)

        multiplier = variables.schrodinger_win_multipliers.get(game_state.num_containers, 1)

        if is_win:
            winnings = int(game_state.bet * multiplier)
            await economy_management_service.update_user_balance(
                interaction.user, winnings, t("economy.reasons.game_win_schrodinger")
            )
            embed = await games_embeds.format_schrodinger_win_embed(winnings, final_choice_index, not was_switched)
        else:
            embed = await games_embeds.format_schrodinger_loss_embed(game_state.bet, game_state.winning_container_index)

        await response_utils.edit_response(interaction, embed=embed, view=None)

        if interaction.message.id in self.games:
            del self.games[interaction.message.id]


schrodinger_game_service = SchrodingerGameService()
