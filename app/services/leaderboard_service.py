from typing import List, Tuple, Optional

from disnake import Embed, Component
from tortoise.functions import Count

from app.config import config
from app.core.enums import Color
from app.core.models import User
from app.utils.ui_utils import ui_utils


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
        total_achievements = len(config.achievements)

        processed_users = []
        if total_achievements > 0:
            for user_id, achievements_count in current_page_users:
                percentage = (achievements_count / total_achievements) * 100
                achievements_str = f"{achievements_count}/{total_achievements} ({percentage:.1f}%)"
                processed_users.append((user_id, achievements_str))

        has_previous = offset > 0

        return processed_users, has_previous, has_next

    @staticmethod
    async def _get_total_articles_users_count() -> int:
        return await User.all().annotate(viewed_count=Count("viewed_objects")).filter(viewed_count__gt=0).count()

    @staticmethod
    async def _get_total_balance_users_count() -> int:
        return await User.all().filter(balance__gt=0).count()

    @staticmethod
    async def _get_total_reputation_users_count() -> int:
        return await User.all().filter(reputation__gt=0).count()

    @staticmethod
    async def _get_total_achievements_users_count() -> int:
        return await User.all().annotate(achievements_count=Count("achievements")).filter(
            achievements_count__gt=0).count()

    async def get_total_users_count(self, chosen_criteria: str) -> Optional[int]:
        if chosen_criteria == "articles":
            return await self._get_total_articles_users_count()
        elif chosen_criteria == "balance":
            return await self._get_total_balance_users_count()
        elif chosen_criteria == "reputation":
            return await self._get_total_reputation_users_count()
        elif chosen_criteria == "achievements":
            return await self._get_total_achievements_users_count()

    async def init_leaderboard_message(self, chosen_criteria: str) -> Optional[Tuple[Embed, List[Component]]]:
        if chosen_criteria == "articles":
            top_users, _, has_next = await self.get_articles_top_users(
                limit=config.leaderboard_items_per_page
            )
            embed = await ui_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за переглянутими статтями",
                hint="Кількість унікальних статей, що були переглянуті користувачем",
                symbol="📚",
                color=Color.CARNATION.value
            )
        elif chosen_criteria == "balance":
            top_users, _, has_next = await self.get_balance_top_users(
                limit=config.leaderboard_items_per_page
            )
            embed = await ui_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за поточною репутацією у фонді",
                hint="Поточний баланс користувача, що може зменшитись за різних дій",
                symbol="💠",
                color=Color.BLUE.value
            )
        elif chosen_criteria == "reputation":
            top_users, _, has_next = await self.get_reputation_top_users(
                limit=config.leaderboard_items_per_page
            )
            embed = await ui_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за загальною репутацією у фонді",
                hint="Загальна репутація користувача, що була зароблена за весь час",
                symbol="🔰",
                color=Color.YELLOW.value
            )
        else:
            top_users, _, has_next = await self.get_achievements_top_users(
                limit=config.leaderboard_items_per_page
            )
            embed = await ui_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за кількістю досягнень",
                hint="Досягнень користувача та відсоткова частка від загальної кількості",
                symbol="🎖️",
                color=Color.HELIOTROPE.value
            )

        components = await ui_utils.init_control_buttons(
            criteria=chosen_criteria,
            disable_first_page_button=True,
            disable_previous_page_button=True,
            disable_next_page_button=not has_next,
            disable_last_page_button=not has_next
        )
        return embed, components

    async def edit_leaderboard_message(
            self, chosen_criteria: str, page: int, offset: int
    ) -> Optional[Tuple[Embed, List[Component]]]:
        if chosen_criteria == "articles":
            top_users, has_previous, has_next = await self.get_articles_top_users(
                limit=config.leaderboard_items_per_page, offset=offset
            )
            embed = await ui_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за переглянутими статтями",
                hint="Кількість унікальних статей, що були переглянуті користувачем",
                symbol="📚",
                color=Color.CARNATION.value,
                offset=offset
            )
        elif chosen_criteria == "balance":
            top_users, has_previous, has_next = await self.get_balance_top_users(
                limit=config.leaderboard_items_per_page, offset=offset
            )
            embed = await ui_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за поточною репутацією у фонді",
                hint="Поточний баланс користувача, що може зменшитись за різних дій",
                symbol="💠",
                color=Color.BLUE.value,
                offset=offset
            )
        elif chosen_criteria == "reputation":
            top_users, has_previous, has_next = await self.get_reputation_top_users(
                limit=config.leaderboard_items_per_page, offset=offset
            )
            embed = await ui_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за загальною репутацією у фонді",
                hint="Загальна репутація користувача, що була зароблена за весь час",
                symbol="🔰",
                color=Color.YELLOW.value,
                offset=offset
            )
        else:
            top_users, has_previous, has_next = await self.get_achievements_top_users(
                limit=config.leaderboard_items_per_page, offset=offset
            )
            embed = await ui_utils.format_leaderboard_embed(
                top_users,
                top_criteria="за кількістю досягнень",
                hint="Досягнень користувача та відсоткова частка від загальної кількості",
                symbol="🎖️",
                color=Color.HELIOTROPE.value,
                offset=offset
            )

        components = await ui_utils.init_control_buttons(
            criteria=chosen_criteria,
            current_page_text=str(page),
            disable_first_page_button=not has_previous,
            disable_previous_page_button=not has_previous,
            disable_next_page_button=not has_next,
            disable_last_page_button=not has_next
        )
        return embed, components


leaderboard_service = LeaderboardService()
