from typing import Optional, List

from disnake import (
    MessageFlags,
    Embed,
    ActionRow,
    TextChannel,
    Message,
    User,
    Forbidden
)

from app.config import logger
from app.core.models import Achievement
from app.localization import t


class ResponseUtils:
    @staticmethod
    async def wait_for_response(interaction) -> None:
        await interaction.send(t("responses.wait"), flags=MessageFlags(suppress_notifications=True))

    @staticmethod
    async def wait_for_ephemeral_response(interaction) -> None:
        await interaction.send(t("responses.wait"), flags=MessageFlags(ephemeral=True))

    @staticmethod
    async def send_response(
            interaction,
            message: Optional[str] = None,
            embed: Optional[Embed] = None,
            components: Optional[List[ActionRow]] = None,
            delete_after: Optional[int] = None
    ) -> None:
        await interaction.edit_original_response(content=message, embed=embed, components=components, delete_after=delete_after)

    @staticmethod
    async def edit_response(
            interaction,
            message: Optional[str] = None,
            embed: Optional[Embed] = None,
            components: Optional[List[ActionRow]] = None,
    ) -> None:
        await interaction.message.edit(content=message, embed=embed, components=components)

    @staticmethod
    async def edit_message(
            message: Message,
            content: Optional[str] = None,
            embed: Optional[Embed] = None,
            components: Optional[List[ActionRow]] = None,
    ) -> None:
        await message.edit(content=content, embed=embed, components=components)

    @staticmethod
    async def send_ephemeral_response(interaction, message: Optional[str] = None) -> None:
        await interaction.send(message, flags=MessageFlags(ephemeral=True))

    @staticmethod
    async def edit_ephemeral_response(
            interaction,
            message: Optional[str] = None,
            embed: Optional[Embed] = None,
            components: Optional[List[ActionRow]] = None,
    ) -> None:
        await interaction.edit_original_response(content=message, embed=embed, components=components)

    @staticmethod
    async def send_new_message(
            channel: TextChannel,
            message: Optional[str] = None,
            embed: Optional[Embed] = None
    ) -> None:
        await channel.send(content=message, embed=embed, flags=MessageFlags(suppress_notifications=True))

    @staticmethod
    async def send_error_response(interaction) -> None:
        await interaction.edit_original_response(content=t("errors.generic"), delete_after=10)

    @staticmethod
    async def send_dm_message(user: User, achievement: Achievement):
        try:
            await user.send(
                content=t(
                    "responses.achievements.dm_notification",
                    name=achievement.name,
                    icon=achievement.icon,
                    description=achievement.description,
                ),
                flags=MessageFlags(suppress_notifications=True),
            )
        except Forbidden:
            logger.warning(f"Could not send DM to user '{user.id}'")


response_utils = ResponseUtils()
