import asyncio
import random

from disnake import ApplicationCommandInteraction, ui, MessageInteraction

from app.core.schemas import CrystallizationState
from app.core.variables import variables
from app.localization import t
from app.services import achievement_handler_service, economy_management_service
from app.utils.response_utils import response_utils
from app.utils.ui_utils import ui_utils


class CrystallizationService:
    @staticmethod
    def _parse_state_from_components(components: list[ui.ActionRow]) -> CrystallizationState:
        state_buttons = components[0].children

        bet_label = state_buttons[0].label
        bet = int(bet_label.split(":")[1].strip().split(" ")[0])

        multiplier_label = state_buttons[1].label
        multiplier = float(multiplier_label.split("x")[1])

        loss_chance_label = state_buttons[2].label
        loss_chance = float(loss_chance_label.split(":")[1].strip().replace("%", ""))

        return CrystallizationState(bet=bet, multiplier=multiplier, loss_chance=loss_chance)

    @staticmethod
    async def start_game(interaction: ApplicationCommandInteraction, bet: int):
        initial_multiplier = round(random.uniform(*variables.crystallize_initial_multiplier_range), 2)
        initial_loss_chance = variables.crystallize_initial_chance * 100

        embed, components = await ui_utils.format_crystallize_embed(
            bet=bet,
            multiplier=initial_multiplier,
            potential_win=int(bet * initial_multiplier),
            loss_chance=initial_loss_chance,
            is_first_turn=True
        )
        await response_utils.send_response(interaction, embed=embed, components=components)

    async def continue_game(self, interaction: MessageInteraction):
        state = self._parse_state_from_components(interaction.message.components)
        current_loss_chance_percent = state.loss_chance

        if random.random() < (current_loss_chance_percent / 100.0):
            loss_embed = await ui_utils.format_crystallize_loss_embed(state.bet)
            await response_utils.edit_response(interaction, embed=loss_embed)
            asyncio.create_task(
                achievement_handler_service.handle_crystallization_achievements(
                    interaction.user, state, is_loss=True
                )
            )
            return

        chance_min, chance_max = variables.crystallize_chance_increment_range
        multiplier_min, multiplier_max = variables.crystallize_multiplier_increment_range

        chance_increment = random.uniform(chance_min, chance_max)

        proportionality_factor = (chance_increment - chance_min) / (chance_max - chance_min)
        multiplier_increment = multiplier_min + proportionality_factor * (multiplier_max - multiplier_min)

        new_loss_chance = current_loss_chance_percent + (chance_increment * 100)

        new_multiplier = round(state.multiplier + multiplier_increment, 2)
        new_potential_win = int(state.bet * new_multiplier)

        embed, components = await ui_utils.format_crystallize_embed(
            bet=state.bet,
            multiplier=new_multiplier,
            potential_win=new_potential_win,
            loss_chance=new_loss_chance,
            is_first_turn=False
        )
        await response_utils.edit_response(interaction, embed=embed, components=components)

    async def cash_out(self, interaction: MessageInteraction):
        winnings_label = interaction.component.label
        winnings = int(winnings_label.split(" ")[1])

        await economy_management_service.update_user_balance(
            interaction.user, winnings, t("economy.reasons.game_win_crystallization")
        )

        state = self._parse_state_from_components(interaction.message.components)
        win_embed = await ui_utils.format_crystallize_win_embed(
            bet=state.bet, winnings=winnings, multiplier=state.multiplier
        )
        await response_utils.edit_response(interaction, embed=win_embed)
        asyncio.create_task(
            achievement_handler_service.handle_crystallization_achievements(
                interaction.user, state, is_loss=False
            )
        )


crystallization_service = CrystallizationService()
