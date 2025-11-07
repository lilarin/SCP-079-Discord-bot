from typing import List, Tuple, Optional

from disnake import Embed, Guild, ui
from disnake.ext.commands import InteractionBot
from tortoise.functions import Count

from app.core.enums import Color
from app.core.models import User
from app.core.variables import variables
from app.embeds import info_embeds
from app.localization import t
from app.views.pagination_view import PaginationView


class LeaderboardService:
    @staticmethod
    async def get_articles_top_users(limit: int, offset: int = 0) -> Tuple[List[Tuple[int, int]], bool, bool]:
        top_users_query = (
            User.all()
            .annotate(viewed_count=Count("viewed_objects"))
            .filter(viewed_count__gt=0)
            .order_by("-viewed_count")
            .offset(offset)
            .limit(limit + 1)
            .values_list("user_id", "viewed_count", flat=False)
        )
        top_users_raw = await top_users_query
        has_next = len(top_users_raw) > limit
        current_page_users = top_users_raw[:limit]
        has_previous = offset > 0
        return current_page_users, has_previous, has_next

    @staticmethod
    async def get_balance_top_users(limit: int, offset: int = 0) -> Tuple[List[Tuple[int, int]], bool, bool]:
        top_users_query = (
            User.all()
            .filter(balance__gt=0)
            .order_by("-balance")
            .offset(offset)
            .limit(limit + 1)
            .values_list("user_id", "balance", flat=False)
        )
        top_users_raw = await top_users_query
        has_next = len(top_users_raw) > limit
        current_page_users = top_users_raw[:limit]
        has_previous = offset > 0
        return current_page_users, has_previous, has_next

    @staticmethod
    async def get_reputation_top_users(limit: int, offset: int = 0) -> Tuple[List[Tuple[int, int]], bool, bool]:
        top_users_query = (
            User.all()
            .filter(reputation__gt=0)
            .order_by("-reputation", "user_id")
            .offset(offset)
            .limit(limit + 1)
            .values_list("user_id", "reputation", flat=False)
        )
        top_users_raw = await top_users_query
        has_next = len(top_users_raw) > limit
        current_page_users = top_users_raw[:limit]
        has_previous = offset > 0
        return current_page_users, has_previous, has_next

    @staticmethod
    async def get_achievements_top_users(limit: int, offset: int = 0) -> Tuple[List[Tuple[int, str]], bool, bool]:
        top_users_query = (
            User.all()
            .annotate(achievements_count=Count("achievements"))
            .filter(achievements_count__gt=0)
            .order_by("-achievements_count")
            .offset(offset)
            .limit(limit + 1)
            .values_list("user_id", "achievements_count", flat=False)
        )
        top_users_raw = await top_users_query
        has_next = len(top_users_raw) > limit
        current_page_users = top_users_raw[:limit]
        total_achievements = len(variables.achievements)
        processed_users = [
            (user_id, f"{count}/{total_achievements} ({(count / total_achievements) * 100:.1f}%)")
            for user_id, count in current_page_users if total_achievements > 0
        ]
        has_previous = offset > 0
        return processed_users, has_previous, has_next

    @staticmethod
    async def get_total_users_count(chosen_criteria: str) -> int:
        criteria_map = {
            "articles": User.all().annotate(c=Count("viewed_objects")).filter(c__gt=0),
            "balance": User.filter(balance__gt=0),
            "reputation": User.filter(reputation__gt=0),
            "achievements": User.all().annotate(c=Count("achievements")).filter(c__gt=0),
        }
        return await criteria_map.get(chosen_criteria, User.all()).count()

    async def init_leaderboard_message(
            self, bot: InteractionBot, guild: Guild, chosen_criteria: str
    ) -> Optional[Tuple[Embed, List[ui.View]]]:
        return await self.edit_leaderboard_message(bot, guild, chosen_criteria, 1, 0, is_init=True)

    async def edit_leaderboard_message(
            self, bot: InteractionBot, guild: Guild, chosen_criteria: str, page: int, offset: int, is_init: bool = False
    ) -> Optional[Tuple[Embed, List[ui.View]]]:
        criteria_map = {
            "articles": (
                self.get_articles_top_users,
                "ui.leaderboard.criteria_articles",
                "ui.leaderboard.hint_articles",
                "📚",
                Color.CARNATION.value
            ),
            "balance": (
                self.get_balance_top_users,
                "ui.leaderboard.criteria_balance",
                "ui.leaderboard.hint_balance",
                "💠",
                Color.BLUE.value
            ),
            "reputation": (
                self.get_reputation_top_users,
                "ui.leaderboard.criteria_reputation",
                "ui.leaderboard.hint_reputation",
                "🔰",
                Color.YELLOW.value
            ),
            "achievements": (
                self.get_achievements_top_users,
                "ui.leaderboard.criteria_achievements",
                "ui.leaderboard.hint_achievements",
                "🎖️",
                Color.HELIOTROPE.value
            ),
        }

        if chosen_criteria not in criteria_map:
            return None

        fetcher, title_key, hint_key, symbol, color = criteria_map[chosen_criteria]
        top_users, has_previous, has_next = await fetcher(limit=variables.leaderboard_items_per_page, offset=offset)

        embed = await info_embeds.format_leaderboard_embed(
            bot, guild, top_users,
            top_criteria=t(title_key), hint=t(hint_key),
            symbol=symbol, color=color, offset=offset
        )
        view = PaginationView(
            criteria=chosen_criteria,
            current_page=page,
            disable_first=is_init or not has_previous,
            disable_previous=is_init or not has_previous,
            disable_next=not has_next,
            disable_last=not has_next
        )
        return embed, [view] if view.children else []


leaderboard_service = LeaderboardService()
