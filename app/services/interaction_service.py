from disnake import Guild, MessageInteraction
from disnake.ext.commands import InteractionBot

from app.config import logger
from app.core.variables import variables
from app.localization import t
from app.services import (
    crystallization_service,
    candy_game_service,
    coguard_service,
    staring_game_service,
    shop_service,
    inventory_service,
    achievement_service,
    leaderboard_service
)
from app.utils.pagination_utils import pagination_utils
from app.utils.response_utils import response_utils


class InteractionService:
    @staticmethod
    async def _get_pagination_params(
            interaction: MessageInteraction, items_per_page: int, total_count: int
    ) -> tuple[int, int]:
        custom_id = interaction.component.custom_id
        if not interaction.message.components or not interaction.message.components[0].children:
            return 1, 0
        current_page_label = interaction.message.components[0].children[2].label
        current_page = int(current_page_label) if current_page_label.isdigit() else 1

        offset = (current_page - 1) * items_per_page
        new_page = current_page

        if "first" in custom_id:
            new_page, offset = 1, 0
        elif "previous" in custom_id:
            new_page = max(1, current_page - 1)
            offset = (new_page - 1) * items_per_page
        elif "next" in custom_id:
            new_page = current_page + 1
            offset = current_page * items_per_page
        elif "last" in custom_id:
            offset, new_page = await pagination_utils.get_last_page_offset(
                total_count=total_count, limit=items_per_page
            )
        return new_page, offset

    @staticmethod
    async def _handle_game_button(interaction: MessageInteraction):
        custom_id = interaction.component.custom_id
        game_actions = {
            "game_crystallize_continue": crystallization_service.continue_game,
            "game_crystallize_stop": crystallization_service.cash_out,
            "game_candy_take": candy_game_service.take_candy,
            "game_candy_leave": candy_game_service.leave_game,
            "game_coguard_higher": lambda inter: coguard_service.play_turn(inter, "higher"),
            "game_coguard_lower": lambda inter: coguard_service.play_turn(inter, "lower"),
            "game_coguard_cashout": coguard_service.cash_out,
            "game_scp173_start": staring_game_service.handle_start,
        }
        if action := game_actions.get(custom_id):
            await action(interaction)

    async def _handle_shop_pagination(self, interaction: MessageInteraction):
        total_count = await shop_service.get_total_items_count()
        new_page, offset = await self._get_pagination_params(
            interaction, variables.shop_items_per_page, total_count
        )
        embed, views = await shop_service.edit_shop_message(new_page, offset)
        await response_utils.edit_response(interaction, embed=embed, view=views[0] if views else None)

    async def _handle_inventory_pagination(self, interaction: MessageInteraction):
        user = interaction.user
        total_count = await inventory_service.get_total_user_items_count(user.id)
        new_page, offset = await self._get_pagination_params(
            interaction, variables.inventory_items_per_page, total_count
        )
        embed, views = await inventory_service.edit_inventory_message(user, new_page, offset)
        await interaction.edit_original_message(embed=embed, view=views[0] if views else None)

    async def _handle_achievements_stats_pagination(self, interaction: MessageInteraction):
        total_count = await achievement_service.get_total_achievements_count()
        new_page, offset = await self._get_pagination_params(
            interaction, variables.achievements_per_page, total_count
        )
        embed, views = await achievement_service.edit_stats_message(new_page, offset)
        await response_utils.edit_ephemeral_response(interaction, embed=embed, view=views[0] if views else None)

    async def _handle_achievements_pagination(self, bot: InteractionBot, interaction: MessageInteraction):
        middle_button_id = interaction.message.components[0].children[2].custom_id
        user_id = interaction.message.interaction_metadata.user.id
        target_user_id = int(middle_button_id) if middle_button_id.isdigit() else user_id
        target_user = await bot.get_or_fetch_user(target_user_id)

        total_count = await achievement_service.get_total_user_achievements_count(target_user.id)
        new_page, offset = await self._get_pagination_params(
            interaction, variables.achievements_per_page, total_count
        )
        embed, views = await achievement_service.edit_achievements_message(target_user, new_page, offset)
        await interaction.edit_original_message(embed=embed, view=views[0] if views else None)

    async def _handle_leaderboard_pagination(
            self, bot: InteractionBot, guild: Guild, interaction: MessageInteraction, criteria: str
    ):
        total_count = await leaderboard_service.get_total_users_count(criteria)
        new_page, offset = await self._get_pagination_params(
            interaction, variables.leaderboard_items_per_page, total_count
        )
        embed, views = await leaderboard_service.edit_leaderboard_message(
            bot, guild, criteria, new_page, offset
        )
        await response_utils.edit_response(interaction, embed=embed, view=views[0] if views else None)

    async def handle_button_click(self, bot: InteractionBot, interaction: MessageInteraction):
        await interaction.response.defer()
        custom_id = interaction.component.custom_id

        if custom_id == "game_scp173_join":
            await staring_game_service.handle_join(interaction)
            return

        if interaction.user.id != interaction.message.interaction_metadata.user.id:
            await response_utils.send_ephemeral_response(
                interaction, t("errors.not_command_author")
            )
            return

        try:
            if custom_id.startswith("game_"):
                await self._handle_game_button(interaction)
            elif "shop" in custom_id:
                await self._handle_shop_pagination(interaction)
            elif "inventory" in custom_id:
                await self._handle_inventory_pagination(interaction)
            elif "achievements_stats" in custom_id:
                await self._handle_achievements_stats_pagination(interaction)
            elif "user_achievements" in custom_id:
                await self._handle_achievements_pagination(bot, interaction)
            else:
                for criteria in variables.leaderboard_options.values():
                    if criteria in custom_id:
                        await self._handle_leaderboard_pagination(bot, interaction.guild, interaction, criteria)
                        break
        except Exception as e:
            logger.error(f"Error handling button click '{custom_id}': {e}", exc_info=True)


interaction_service = InteractionService()
