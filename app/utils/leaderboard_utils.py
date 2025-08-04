import asyncio
from typing import List, Tuple

import disnake


class LeaderboardUtils:
    @staticmethod
    async def format_leaderboard_embed(
            top_users: List[Tuple[int, int]], top_criteria: str, hint: str, symbol: str, color: str
    ) -> disnake.Embed:
        embed = disnake.Embed(
            title=f"Топ користувачів {top_criteria}",
            color=int(color.lstrip("#"), 16),
        )

        from app.bot import bot

        user_fetch_tasks = [bot.get_or_fetch_user(user_id) for user_id, _ in top_users]

        fetched_users = await asyncio.gather(*user_fetch_tasks)

        description_lines = []
        for i, (user_id, count) in enumerate(top_users, 1):
            user = fetched_users[i - 1]
            if user:
                description_lines.append(f"{i}. {user.mention} (`{user.name}`) – **{count} {symbol}**")

        embed.description = "\n".join(description_lines)
        embed.description += f"\n-# {hint}"
        return embed


leaderboard_utils = LeaderboardUtils()
