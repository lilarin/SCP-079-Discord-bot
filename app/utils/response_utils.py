from typing import Optional

from disnake import MessageFlags, Embed


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
            embed: Optional[Embed] = None
    ) -> None:
        if embed:
            await interaction.edit_original_response(content=message, embed=embed)
        else:
            await interaction.edit_original_response(content=message)

    @staticmethod
    async def send_ephemeral_response(interaction, message: Optional[str] = None) -> None:
        await interaction.send(message, flags=MessageFlags(ephemeral=True))


response_utils = ResponseUtils()
