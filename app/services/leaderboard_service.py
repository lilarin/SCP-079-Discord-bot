import math
from typing import List, Tuple

from tortoise.functions import Count

from app.models import User


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
            .order_by("-reputation")
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
    async def get_total_articles_users_count() -> int:
        return await User.all().annotate(viewed_count=Count("viewed_objects")).filter(viewed_count__gt=0).count()

    @staticmethod
    async def get_total_balance_users_count() -> int:
        return await User.all().filter(balance__gt=0).count()

    @staticmethod
    async def get_total_reputation_users_count() -> int:
        return await User.all().filter(reputation__gt=0).count()

    @staticmethod
    def get_last_page_offset(total_count: int, limit: int) -> int:
        if total_count == 0:
            return 0
        total_pages = math.ceil(total_count / limit)
        offset = max(0, (total_pages - 1) * limit)
        return offset


leaderboard_service = LeaderboardService()
