from typing import Optional

from disnake import Embed, File, Role

from app.core.variables import variables
from app.localization import t


async def format_new_user_embed(user_mention: str, card: File, color: int) -> Embed:
    embed = Embed(
        description=t("ui.new_user_welcome", user_mention=user_mention),
        color=color
    )
    embed.set_image(file=card)
    return embed


async def format_user_embed(
        card: File,
        color: int,
        achievements_count: int,
        dossier: Optional[str] = None,
        role: Optional[Role] = None,
) -> Embed:
    embed = Embed(
        title=t("ui.user_card.title"),
        color=color
    )
    embed.set_image(file=card)

    if role:
        embed.add_field(name=t("ui.user_card.role_field"), value=role.mention, inline=False)

    if achievements_count > 0:
        embed.add_field(
            name=t("ui.user_card.achievements_field"),
            value=f"{achievements_count} / {len(variables.achievements)}",
            inline=False,
        )

    if dossier:
        embed.add_field(name=t("ui.user_card.dossier_field"), value=dossier, inline=False)

    return embed
