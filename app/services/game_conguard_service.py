import asyncio
import random

import disnake

from app.config import config
from app.core.schemas import CoguardState
from app.services import achievement_handler_service, economy_management_service
from app.utils.response_utils import response_utils
from app.utils.ui_utils import ui_utils


class CoguardService:
    @staticmethod
    def _parse_state_from_components(components: list[disnake.ui.ActionRow]) -> CoguardState:
        state_buttons = components[0].children

        bet_label = state_buttons[0].label
        bet = int(bet_label.split(':')[1].strip().split(' ')[0])

        multiplier_label = state_buttons[1].label
        multiplier = float(multiplier_label.split('x')[1])

        number_label = state_buttons[2].label
        current_number = int(number_label.split(':')[1].strip())

        streak_label = state_buttons[3].label
        win_streak = int(streak_label.split(':')[1].strip())

        return CoguardState(
            bet=bet,
            multiplier=multiplier,
            current_number=current_number,
            win_streak=win_streak
        )

    @staticmethod
    async def start_game(interaction: disnake.ApplicationCommandInteraction, bet: int):
        initial_multiplier = round(random.uniform(*config.coguard_initial_multiplier_range), 2)
        initial_number = random.randint(1, 100)

        embed, components = await ui_utils.format_coguard_embed(
            bet=bet,
            multiplier=initial_multiplier,
            potential_win=int(bet * initial_multiplier),
            current_number=initial_number,
            win_streak=0,
            is_first_turn=True
        )
        await response_utils.send_response(interaction, embed=embed, components=components)

    async def play_turn(self, interaction: disnake.MessageInteraction, choice: str):
        state = self._parse_state_from_components(interaction.message.components)

        new_number = random.randint(1, 100)
        while new_number == state.current_number:
            new_number = random.randint(1, 100)

        higher_correct = choice == "higher" and new_number > state.current_number
        lower_correct = choice == "lower" and new_number < state.current_number
        is_correct = higher_correct or lower_correct

        if not is_correct:
            loss_embed = await ui_utils.format_coguard_loss_embed(state.bet, state.win_streak)
            await response_utils.edit_response(interaction, embed=loss_embed)
            asyncio.create_task(achievement_handler_service.handle_coguard_achievements(
                interaction.user, state, is_loss=True
            ))
            return

        new_win_streak = state.win_streak + 1
        multiplier_increment = random.uniform(*config.coguard_multiplier_increment_range)
        new_multiplier = round(state.multiplier + multiplier_increment, 2)
        new_potential_win = int(state.bet * new_multiplier)

        embed, components = await ui_utils.format_coguard_embed(
            bet=state.bet,
            multiplier=new_multiplier,
            potential_win=new_potential_win,
            current_number=new_number,
            win_streak=new_win_streak
        )
        await response_utils.edit_response(interaction, embed=embed, components=components)

    async def cash_out(self, interaction: disnake.MessageInteraction):
        winnings_label = interaction.component.label
        winnings = int(winnings_label.split(' ')[1])

        await economy_management_service.update_user_balance(
            interaction.user, winnings, f"Перемога у грі `когнітивна-стійкість`"
        )

        state = self._parse_state_from_components(interaction.message.components)
        win_embed = await ui_utils.format_coguard_win_embed(
            bet=state.bet,
            winnings=winnings,
            multiplier=state.multiplier,
            win_streak=state.win_streak
        )
        await response_utils.edit_response(interaction, embed=win_embed)

        asyncio.create_task(achievement_handler_service.handle_coguard_achievements(
            interaction.user, state, is_loss=False
        ))


coguard_service = CoguardService()
