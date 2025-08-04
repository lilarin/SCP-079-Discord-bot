import math
from typing import List, Tuple, Optional

from disnake import Embed, Component
from tortoise.functions import Count

from app.models import User
from app.utils.leaderboard_utils import leaderboard_utils


class LeaderboardService:
    @staticmethod
    async def get_articles_top_users(limit: int = 10, offset: int = 0) -> Tuple[List[Tuple[int, int]], bool, bool]:
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
    async def get_balance_top_users(limit: int = 10, offset: int = 0) -> Tuple[List[Tuple[int, int]], bool, bool]:
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
    async def get_reputation_top_users(limit: int = 10, offset: int = 0) -> Tuple[List[Tuple[int, int]], bool, bool]:
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
    async def _get_total_articles_users_count() -> int:
        return await User.all().annotate(viewed_count=Count("viewed_objects")).filter(viewed_count__gt=0).count()

    @staticmethod
    async def _get_total_balance_users_count() -> int:
        return await User.all().filter(balance__gt=0).count()

    @staticmethod
    async def _get_total_reputation_users_count() -> int:
        return await User.all().filter(reputation__gt=0).count()

    async def get_total_users_count(self, chosen_criteria: str) -> Optional[int]:
        if chosen_criteria == "articles":
            return await self._get_total_articles_users_count()
        elif chosen_criteria == "balance":
            return await self._get_total_balance_users_count()
        elif chosen_criteria == "reputation":
            return await self._get_total_reputation_users_count()

    @staticmethod
    async def get_last_page_offset(total_count: int, limit: int = 10) -> Tuple[int, int]:
        if total_count == 0:
            return 0, 0
        total_pages = math.ceil(total_count / limit)
        offset = max(0, (total_pages - 1) * limit)
        return offset, total_pages

    @staticmethod
    async def init_leaderboard_message(chosen_criteria: str) -> Optional[Tuple[Embed, List[Component]]]:
        if chosen_criteria == "articles":
            top_users, _, has_next = await leaderboard_service.get_articles_top_users()
            embed = await leaderboard_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за переглянутими статтями",
                hint="Кількість унікальних статей, що були переглянуті користувачем",
                symbol="📚",
                color="#f5575a"
            )
            components = await leaderboard_utils.init_leaderboard_buttons(
                criteria=chosen_criteria,
                disable_first_page_button=True,
                disable_previous_page_button=True,
                disable_next_page_button=not has_next,
                disable_last_page_button=not has_next
            )
            return embed, components

        elif chosen_criteria == "balance":
            top_users, _, has_next = await leaderboard_service.get_balance_top_users()
            embed = await leaderboard_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за поточною репутацією у фонді",
                hint="Поточний баланс користувача, що може зменшитись за різних дій",
                symbol="💠",
                color="#57b1f5"
            )
            components = await leaderboard_utils.init_leaderboard_buttons(
                criteria=chosen_criteria,
                disable_first_page_button=True,
                disable_previous_page_button=True,
                disable_next_page_button=not has_next,
                disable_last_page_button=not has_next
            )
            return embed, components

        elif chosen_criteria == "reputation":
            top_users, _, has_next = await leaderboard_service.get_reputation_top_users()
            embed = await leaderboard_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за загальною репутацією у фонді",
                hint="Загальна репутація користувача, що була зароблена за весь час",
                symbol="🔰",
                color="#FFD700"
            )
            components = await leaderboard_utils.init_leaderboard_buttons(
                criteria=chosen_criteria,
                disable_first_page_button=True,
                disable_previous_page_button=True,
                disable_next_page_button=not has_next,
                disable_last_page_button=not has_next
            )
            return embed, components

    @staticmethod
    async def edit_leaderboard_message(chosen_criteria: str, page: int, offset: int) -> Optional[Tuple[Embed, List[Component]]]:
        if chosen_criteria == "articles":
            top_users, has_previous, has_next = await leaderboard_service.get_articles_top_users(offset=offset)
            embed = await leaderboard_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за переглянутими статтями",
                hint="Кількість унікальних статей, що були переглянуті користувачем",
                symbol="📚",
                color="#f5575a",
                offset=offset
            )
            components = await leaderboard_utils.init_leaderboard_buttons(
                criteria=chosen_criteria,
                current_page_text=page,
                disable_first_page_button=not has_previous,
                disable_previous_page_button=not has_previous,
                disable_next_page_button=not has_next,
                disable_last_page_button=not has_next
            )
            return embed, components

        elif chosen_criteria == "balance":
            top_users, has_previous, has_next = await leaderboard_service.get_balance_top_users(offset=offset)
            embed = await leaderboard_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за поточною репутацією у фонді",
                hint="Поточний баланс користувача, що може зменшитись за різних дій",
                symbol="💠",
                color="#57b1f5",
                offset=offset
            )
            components = await leaderboard_utils.init_leaderboard_buttons(
                criteria=chosen_criteria,
                current_page_text=page,
                disable_first_page_button=not has_previous,
                disable_previous_page_button=not has_previous,
                disable_next_page_button=not has_next,
                disable_last_page_button=not has_next
            )
            return embed, components

        elif chosen_criteria == "reputation":
            top_users, has_previous, has_next = await leaderboard_service.get_reputation_top_users(offset=offset)
            embed = await leaderboard_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за загальною репутацією у фонді",
                hint="Загальна репутація користувача, що була зароблена за весь час",
                symbol="🔰",
                color="#FFD700",
                offset=offset
            )
            components = await leaderboard_utils.init_leaderboard_buttons(
                criteria=chosen_criteria,
                current_page_text=page,
                disable_first_page_button=not has_previous,
                disable_previous_page_button=not has_previous,
                disable_next_page_button=not has_next,
                disable_last_page_button=not has_next
            )
            return embed, components


leaderboard_service = LeaderboardService()
