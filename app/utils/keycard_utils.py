from typing import Optional

from disnake import Embed, File, Role


class KeyCardUtils:
    @staticmethod
    async def process_username(user_name: str) -> str:
        user_name = user_name.upper()
        if len(user_name) > 14:
            user_name = (user_name[:12].strip() + "..")
        return user_name

    @staticmethod
    async def get_user_code(timestamp: float) -> str:
        return "-".join(str(round(timestamp, 1)).split("."))

    @staticmethod
    async def format_new_user_embed(user_mention: str, card: File, color: int) -> Embed:
        embed = Embed(
            description=f"Вітаємо {user_mention} у складі співробітників фонду!",
            color=color
        )
        embed.set_image(file=card)

        return embed

    @staticmethod
    async def format_user_embed(
            card: File, color: int, dossier: Optional[str] = None, role: Optional[Role] = None
    ) -> Embed:
        embed = Embed(
            title="Інформація про співробітника фонду",
            color=color
        )
        embed.set_image(file=card)

        if role:
            embed.add_field(name="Посада:", value=role.mention, inline=False)
        if dossier:
            embed.add_field(name="Досьє:", value=dossier, inline=False)

        return embed


keycard_utils = KeyCardUtils()
