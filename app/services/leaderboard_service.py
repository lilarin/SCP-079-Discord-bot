from typing import List, Tuple

from tortoise.functions import Count

from app.models import User


class LeaderboardService:
    @staticmethod
    async def get_articles_top_users(limit: int = 10, offset: int = 0) -> List[Tuple[int, int]]:
        top_users_query = (
            User.all()
            .annotate(viewed_count=Count("viewed_objects"))
            .filter(viewed_count__gt=0)
            .order_by("-viewed_count")
            .offset(offset)
            .limit(limit)
            .values_list("user_id", "viewed_count", flat=False)
        )
        top_users = await top_users_query
        return top_users

    @staticmethod
    async def get_balance_top_users(limit: int = 10, offset: int = 0) -> List[Tuple[int, int]]:
        top_users_query = (
            User.all()
            .filter(balance__gt=0)
            .order_by("-balance")
            .offset(offset)
            .limit(limit)
            .values_list("user_id", "balance", flat=False)
        )
        top_users = await top_users_query
        return top_users

    @staticmethod
    async def get_reputation_top_users(limit: int = 10, offset: int = 0) -> List[Tuple[int, int]]:
        top_users_query = (
            User.all()
            .filter(reputation__gt=0)
            .order_by("-reputation")
            .offset(offset)
            .limit(limit)
            .values_list("user_id", "reputation", flat=False)
        )
        top_users = await top_users_query
        return top_users


leaderboard_service = LeaderboardService()
