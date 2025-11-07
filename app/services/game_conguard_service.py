import asyncio
import random

from disnake import ui, ApplicationCommandInteraction, MessageInteraction

from app.core.schemas import CoguardState
from app.core.variables import variables
from app.embeds import games_embeds
from app.localization import t
from app.services import achievement_handler_service, economy_management_service
from app.utils.response_utils import response_utils
from app.views.games_views import CoguardView


class CoguardService:
    @staticmethod
    def _parse_state_from_components(components: list[ui.ActionRow]) -> CoguardState:
        state_buttons = components[0].children
        bet_label = state_buttons[0].label
        bet = int(bet_label.split(":")[1].strip().split(" ")[0])
        multiplier_label = state_buttons[1].label
        multiplier = float(multiplier_label.split("x")[1])
        number_label = state_buttons[2].label
        current_number = int(number_label.split(":")[1].strip())
        streak_label = state_buttons[3].label
        win_streak = int(streak_label.split(":")[1].strip())
        return CoguardState(bet=bet, multiplier=multiplier, current_number=current_number, win_streak=win_streak)

    @staticmethod
    async def start_game(interaction: ApplicationCommandInteraction, bet: int):
        multiplier = round(random.uniform(*variables.coguard_initial_multiplier_range), 2)
        number = random.randint(1, 100)

        embed = await games_embeds.format_coguard_embed(current_number=number)
        view = CoguardView(
            bet=bet,
            multiplier=multiplier,
            potential_win=int(bet * multiplier),
            current_number=number,
            win_streak=0,
            is_first_turn=True
        )
        await response_utils.send_response(interaction, embed=embed, view=view)

    async def play_turn(self, interaction: MessageInteraction, choice: str):
        state = self._parse_state_from_components(interaction.message.components)
        new_number = random.randint(1, 100)
        while new_number == state.current_number:
            new_number = random.randint(1, 100)

        is_correct = (choice == "higher" and new_number > state.current_number) or \
                     (choice == "lower" and new_number < state.current_number)

        if not is_correct:
            loss_embed = await games_embeds.format_coguard_loss_embed(state.bet, state.win_streak)
            await response_utils.edit_response(interaction, embed=loss_embed, view=None)
            asyncio.create_task(
                achievement_handler_service.handle_coguard_achievements(interaction.user, state, is_loss=True)
            )
            return

        new_win_streak = state.win_streak + 1
        multiplier_increment = random.uniform(*variables.coguard_multiplier_increment_range)
        new_multiplier = round(state.multiplier + multiplier_increment, 2)

        embed = await games_embeds.format_coguard_embed(current_number=new_number)
        view = CoguardView(
            bet=state.bet,
            multiplier=new_multiplier,
            potential_win=int(state.bet * new_multiplier),
            current_number=new_number,
            win_streak=new_win_streak,
            is_first_turn=False
        )
        await response_utils.edit_response(interaction, embed=embed, view=view)

    async def cash_out(self, interaction: MessageInteraction):
        winnings_label = interaction.component.label
        winnings = int(winnings_label.split(" ")[1])

        await economy_management_service.update_user_balance(
            interaction.user, winnings, t("economy.reasons.game_win_coguard")
        )

        state = self._parse_state_from_components(interaction.message.components)
        win_embed = await games_embeds.format_coguard_win_embed(
            bet=state.bet,
            winnings=winnings,
            multiplier=state.multiplier,
            win_streak=state.win_streak,
        )
        await response_utils.edit_response(interaction, embed=win_embed, view=None)
        asyncio.create_task(
            achievement_handler_service.handle_coguard_achievements(interaction.user, state, is_loss=False)
        )


coguard_service = CoguardService()
