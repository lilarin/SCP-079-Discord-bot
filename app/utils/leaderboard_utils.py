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

    @staticmethod
    async def init_leaderboard_buttons(
            criteria: str,
            current_page_text: str = "1",
            disable_first_page_button: bool = False,
            disable_previous_page_button: bool = False,
            disable_next_page_button: bool = False,
            disable_last_page_button: bool = False,
    ) -> disnake.ui.ActionRow:
        first_page_button = disnake.ui.Button(
            style=disnake.ButtonStyle.grey,
            label="🡸",
            custom_id=f"first_page_{criteria}_button",
            disabled=disable_first_page_button,
        )
        previous_page_button = disnake.ui.Button(
            style=disnake.ButtonStyle.grey,
            label="❮",
            custom_id=f"previous_page_{criteria}_button",
            disabled=disable_previous_page_button,
        )
        current_page_button = disnake.ui.Button(
            style=disnake.ButtonStyle.grey,
            label=current_page_text,
            custom_id=f"current_page_{criteria}_button",
            disabled=True,
        )
        next_page_button = disnake.ui.Button(
            style=disnake.ButtonStyle.grey,
            label="❯",
            custom_id=f"next_page_{criteria}_button",
            disabled=disable_next_page_button,
        )
        last_page_button = disnake.ui.Button(
            style=disnake.ButtonStyle.grey,
            label="🡺",
            custom_id=f"last_page_{criteria}_button",
            disabled=disable_last_page_button,
        )
        return disnake.ui.ActionRow(
            first_page_button, previous_page_button, current_page_button, next_page_button, last_page_button,
        )


leaderboard_utils = LeaderboardUtils()
