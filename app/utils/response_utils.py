from typing import Optional, List

from disnake import MessageFlags, Embed, ActionRow


class ResponseUtils:
    @staticmethod
    async def wait_for_response(interaction) -> None:
        await interaction.send(f"Очікуйте...", flags=MessageFlags(suppress_notifications=True))

    @staticmethod
    async def wait_for_ephemeral_response(interaction) -> None:
        await interaction.send(f"Очікуйте...", flags=MessageFlags(ephemeral=True))

    @staticmethod
    async def send_response(
            interaction,
            message: Optional[str] = None,
            embed: Optional[Embed] = None,
            components: Optional[List[ActionRow]] = None,
            delete_after: Optional[int] = None
    ) -> None:
        if embed:
            await interaction.edit_original_response(content=message, embed=embed, components=components)
        else:
            await interaction.edit_original_response(content=message, delete_after=delete_after)

    @staticmethod
    async def edit_response(
            interaction,
            message: Optional[str] = None,
            embed: Optional[Embed] = None,
            components: Optional[List[ActionRow]] = None,
    ) -> None:
        await interaction.message.edit(content=message, embed=embed, components=components)

    @staticmethod
    async def send_ephemeral_response(interaction, message: Optional[str] = None) -> None:
        await interaction.send(message, flags=MessageFlags(ephemeral=True))

    @staticmethod
    async def edit_ephemeral_response(interaction, message: Optional[str] = None) -> None:
        await interaction.edit_original_response(content=message)


response_utils = ResponseUtils()
