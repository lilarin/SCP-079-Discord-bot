import asyncio
from typing import List, Tuple

from disnake import Embed, File, User, Member, Guild
from disnake.ext.commands import InteractionBot

from app.core.enums import Color
from app.core.models import SCPObject, Achievement
from app.core.variables import variables
from app.localization import t


async def format_leaderboard_embed(
        bot: InteractionBot,
        guild: Guild,
        top_users: List[Tuple[int, int]],
        top_criteria: str,
        hint: str,
        symbol: str,
        color: int,
        offset: int = 0
) -> Embed:
    embed = Embed(
        title=t("ui.leaderboard.title", top_criteria=top_criteria),
        color=color,
    )

    if not top_users:
        embed.description = t("ui.leaderboard.no_users")
        embed.description += f"\n-# {hint}"
        return embed

    user_ids = [user_id for user_id, _ in top_users]

    fetched_members: List[Member] = await guild.get_or_fetch_members(user_ids)
    fetched_member_ids = {member.id for member in fetched_members}

    missing_user_ids = [user_id for user_id in user_ids if user_id not in fetched_member_ids]

    fallback_users: List[User] = []
    if missing_user_ids:
        user_fetch_tasks = [bot.get_or_fetch_user(user_id) for user_id in missing_user_ids]
        fallback_users = await asyncio.gather(*user_fetch_tasks)

    all_fetched_users = {user.id: user for user in fetched_members + fallback_users if user}

    description_lines = []
    for i, (user_id, count) in enumerate(top_users, 1):
        user = all_fetched_users.get(user_id)
        if user:
            description_lines.append(
                f"{i + offset}. {user.mention} (`{user.name}`) – **{count} {symbol}**"
            )

    if description_lines:
        embed.description = "\n".join(description_lines)
    else:
        embed.description = t("ui.leaderboard.fetch_error")

    embed.description += f"\n-# {hint}"
    return embed


async def format_article_embed(article: SCPObject, image_file: File) -> Embed:
    embed_color = int(variables.scp_class_config[article.object_class][0].lstrip("#"), 16)
    embed = Embed(color=embed_color)
    embed.set_image(file=image_file)
    return embed


async def format_achievements_embed(
        target_user: User | Member, achievements: List[Achievement], offset: int = 0
) -> Embed:
    embed = Embed(
        title=t("ui.achievements.user_title", user_name=target_user.display_name),
        color=Color.YELLOW.value
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)

    if not achievements:
        embed.description = t("ui.achievements.no_achievements")
    else:
        description_lines = [
            f"{offset + i + 1}. **{ach.name}** {ach.icon} \n-# {ach.description}"
            for i, ach in enumerate(achievements)
        ]
        embed.description = "\n\n".join(description_lines)

    return embed


async def format_achievement_stats_embed(
        stats: List[Tuple[Achievement, int]], total_players: int, offset: int = 0
) -> Embed:
    embed = Embed(
        title=t("ui.achievements.stats_title"),
        color=Color.ORANGE.value
    )

    description_lines = []
    for i, (ach, count) in enumerate(stats):
        percentage = (count / total_players) * 100 if total_players > 0 else 0
        description_lines.append(
            f"{offset + i + 1}. **{ach.name}** {ach.icon} ({percentage:.1f}%)\n"
            f"-# {ach.description}"
        )

    embed.description = "\n\n".join(description_lines)
    return embed


async def format_games_info_embed() -> Embed:
    embed = Embed(
        title=t("ui.games_info.title"),
        description=t("ui.games_info.description"),
        color=Color.WHITE.value
    )
    embed.set_image(url="https://imgur.com/dzOcnnY.png")

    embed.add_field(
        name=t("ui.games_info.crystallization_name"),
        value=t("ui.games_info.crystallization_desc"),
        inline=False
    )
    embed.add_field(
        name=t("ui.games_info.coin_name"),
        value=t("ui.games_info.coin_desc"),
        inline=False
    )
    embed.add_field(
        name=t("ui.games_info.candy_name"),
        value=t("ui.games_info.candy_desc"),
        inline=False
    )
    embed.add_field(
        name=t("ui.games_info.coguard_name"),
        value=t("ui.games_info.coguard_desc"),
        inline=False
    )
    embed.add_field(
        name=t("ui.games_info.staring_name"),
        value=t("ui.games_info.staring_desc"),
        inline=False
    )
    embed.add_field(
        name=t("ui.games_info.schrodinger_name"),
        value=t("ui.games_info.schrodinger_desc"),
        inline=False
    )
    embed.add_field(
        name=t("ui.games_info.hole_name"),
        value=t("ui.games_info.hole_desc"),
        inline=False
    )
    return embed
