from disnake import Guild, MessageInteraction
from disnake.ext.commands import InteractionBot

from app.config import config, logger
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
        current_page = int(interaction.message.components[0].children[2].label)

        offset = 0
        new_page = 1

        if "previous" in custom_id:
            new_page = current_page - 1
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

        if custom_id == "game_crystallize_continue":
            await crystallization_service.continue_game(interaction)
        elif custom_id == "game_crystallize_stop":
            await crystallization_service.cash_out(interaction)
        elif custom_id == "game_candy_take":
            await candy_game_service.take_candy(interaction)
        elif custom_id == "game_candy_leave":
            await candy_game_service.leave_game(interaction)
        elif custom_id == "game_coguard_higher":
            await coguard_service.play_turn(interaction, "higher")
        elif custom_id == "game_coguard_lower":
            await coguard_service.play_turn(interaction, "lower")
        elif custom_id == "game_coguard_cashout":
            await coguard_service.cash_out(interaction)
        elif custom_id == "game_scp173_start":
            await staring_game_service.handle_start(interaction)

    async def _handle_shop_pagination(self, interaction: MessageInteraction):
        total_count = await shop_service.get_total_items_count()
        new_page, offset = await self._get_pagination_params(
            interaction, config.shop_items_per_page, total_count
        )

        embed, components = await shop_service.edit_shop_message(new_page, offset)
        await response_utils.edit_response(interaction, embed=embed, components=components)

    async def _handle_inventory_pagination(self, interaction: MessageInteraction):
        user = interaction.user
        total_count = await inventory_service.get_total_user_items_count(user.id)
        new_page, offset = await self._get_pagination_params(
            interaction, config.inventory_items_per_page, total_count
        )

        embed, components = await inventory_service.edit_inventory_message(user, new_page, offset)
        await interaction.edit_original_message(embed=embed, components=components)

    async def _handle_achievements_stats_pagination(self, interaction: MessageInteraction):
        total_count = await achievement_service.get_total_achievements_count()
        new_page, offset = await self._get_pagination_params(
            interaction, config.achievements_per_page, total_count
        )

        embed, components = await achievement_service.edit_stats_message(new_page, offset)
        await response_utils.edit_ephemeral_response(interaction, embed=embed, components=components)

    async def _handle_achievements_pagination(self, bot: InteractionBot, interaction: MessageInteraction):
        middle_button_id = interaction.message.components[0].children[2].custom_id

        if middle_button_id.isdigit() and int(middle_button_id) != interaction.message.interaction_metadata.user.id:
            target_user = await bot.get_or_fetch_user(int(middle_button_id))
        else:
            target_user = interaction.message.interaction_metadata.user

        total_count = await achievement_service.get_total_user_achievements_count(target_user.id)
        new_page, offset = await self._get_pagination_params(
            interaction, config.achievements_per_page, total_count
        )

        embed, components = await achievement_service.edit_achievements_message(target_user, new_page, offset)
        await interaction.edit_original_message(embed=embed, components=components)

    async def _handle_leaderboard_pagination(
            self, bot: InteractionBot, guild: Guild, interaction: MessageInteraction, criteria: str
    ):
        total_count = await leaderboard_service.get_total_users_count(criteria)
        new_page, offset = await self._get_pagination_params(
            interaction, config.leaderboard_items_per_page, total_count
        )
        embed, components = await leaderboard_service.edit_leaderboard_message(
            bot, guild, criteria, new_page, offset
        )
        await response_utils.edit_response(interaction, embed=embed, components=components)

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
                return

            if "shop" in custom_id:
                await self._handle_shop_pagination(interaction)
            elif "inventory" in custom_id:
                await self._handle_inventory_pagination(interaction)
            elif "achievements_stats" in custom_id:
                await self._handle_achievements_stats_pagination(interaction)
            elif "user_achievements" in custom_id:
                await self._handle_achievements_pagination(bot, interaction)
            else:
                for criteria in config.leaderboard_options.values():
                    if criteria in custom_id:
                        await self._handle_leaderboard_pagination(bot, interaction.guild, interaction, criteria)
                        break
        except Exception as e:
            logger.error(f"Error handling button click '{custom_id}': {e}")


interaction_service = InteractionService()
