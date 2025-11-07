from typing import Dict, List, Tuple, Optional

from disnake import Embed, User, Member, ui
from tortoise.functions import Count

from app.config import logger
from app.core.models import Achievement, User as UserModel, UserAchievement
from app.core.schemas import AchievementConfig
from app.core.variables import variables
from app.embeds import info_embeds
from app.views.pagination_view import PaginationView


class AchievementService:
    def __init__(self):
        self.achievements_config: Dict[str, AchievementConfig] = variables.achievements

    async def sync_achievements(self) -> None:
        if not self.achievements_config:
            logger.warning("Achievement configuration is empty. Skipping synchronization")
            return

        logger.info("Starting achievement synchronization...")
        db_achievements = {ach.achievement_id: ach async for ach in Achievement.all()}
        config_ids = set(self.achievements_config.keys())
        db_ids = set(db_achievements.keys())

        to_delete_ids = db_ids - config_ids
        if to_delete_ids:
            await Achievement.filter(achievement_id__in=to_delete_ids).delete()
            logger.info(f"Deleted {len(to_delete_ids)} obsolete achievements")

        for ach_id, ach_data in self.achievements_config.items():
            db_ach = db_achievements.get(ach_id)
            if not db_ach:
                await Achievement.create(
                    achievement_id=ach_id,
                    name=ach_data.name,
                    description=ach_data.description,
                    icon=ach_data.icon
                )
                logger.info(f"Created new achievement: {ach_data.name}")
            elif (db_ach.name != ach_data.name or
                  db_ach.description != ach_data.description or
                  db_ach.icon != ach_data.icon):
                db_ach.name = ach_data.name
                db_ach.description = ach_data.description
                db_ach.icon = ach_data.icon
                await db_ach.save()
                logger.info(f"Updated achievement: {ach_data.name}")
        logger.info("Achievement synchronization complete")

    @staticmethod
    async def _get_paginated_user_achievements(
            user_id: int, limit: int, offset: int = 0
    ) -> Tuple[List[Achievement], bool, bool]:
        db_user, _ = await UserModel.get_or_create(user_id=user_id)
        user_achievements_query = UserAchievement.filter(user=db_user).select_related("achievement").order_by(
            "achievement__id").offset(offset).limit(limit + 1)
        user_achievements_raw = await user_achievements_query
        achievements_raw = [ua.achievement for ua in user_achievements_raw]

        has_next = len(achievements_raw) > limit
        current_page_items = achievements_raw[:limit]
        has_previous = offset > 0

        return current_page_items, has_previous, has_next

    @staticmethod
    async def get_total_user_achievements_count(user_id: int) -> int:
        user, _ = await UserModel.get_or_create(user_id=user_id)
        return await UserAchievement.filter(user=user).count()

    async def init_achievements_message(self, user: Member | User) -> Optional[Tuple[Embed, List[ui.View]]]:
        items, _, has_next = await self._get_paginated_user_achievements(
            user_id=user.id, limit=variables.achievements_per_page
        )

        embed = await info_embeds.format_achievements_embed(user, items)
        view = PaginationView(
            criteria="user_achievements",
            disable_first=True,
            disable_previous=True,
            disable_next=not has_next,
            disable_last=not has_next,
            target_user_id=user.id
        )
        return embed, [view] if view.children else []

    async def edit_achievements_message(
            self, user: User, page: int, offset: int
    ) -> Optional[Tuple[Embed, List[ui.View]]]:
        items, has_previous, has_next = await self._get_paginated_user_achievements(
            user_id=user.id, limit=variables.achievements_per_page, offset=offset
        )

        embed = await info_embeds.format_achievements_embed(user, items, offset=offset)
        view = PaginationView(
            criteria="user_achievements",
            current_page=page,
            disable_first=not has_previous,
            disable_previous=not has_previous,
            disable_next=not has_next,
            disable_last=not has_next,
            target_user_id=user.id
        )
        return embed, [view] if view.children else []

    @staticmethod
    async def get_achievements_statistics(
            limit: int, offset: int = 0
    ) -> Tuple[List[Tuple[Achievement, int]], bool, bool]:
        stats_query = (
            Achievement.all()
            .annotate(owners_count=Count("users"))
            .order_by("-owners_count", "id")
            .offset(offset)
            .limit(limit + 1)
        )
        stats_raw = await stats_query
        stats_list = [(ach, ach.owners_count) for ach in stats_raw]

        has_next = len(stats_list) > limit
        current_page_items = stats_list[:limit]
        has_previous = offset > 0

        return current_page_items, has_previous, has_next

    @staticmethod
    async def get_total_players_with_achievements_count() -> int:
        return await UserModel.filter(achievements__id__isnull=False).distinct().count()

    @staticmethod
    async def get_total_achievements_count() -> int:
        return await Achievement.all().count()

    async def init_stats_message(self) -> Optional[Tuple[Embed, List[ui.View]]]:
        stats, _, has_next = await self.get_achievements_statistics(
            limit=variables.achievements_per_page
        )
        total_players = await self.get_total_players_with_achievements_count()
        embed = await info_embeds.format_achievement_stats_embed(stats, total_players)
        view = PaginationView(
            criteria="achievements_stats",
            disable_first=True,
            disable_previous=True,
            disable_next=not has_next,
            disable_last=not has_next
        )
        return embed, [view] if view.children else []

    async def edit_stats_message(self, page: int, offset: int) -> Optional[Tuple[Embed, List[ui.View]]]:
        stats, has_previous, has_next = await self.get_achievements_statistics(
            limit=variables.achievements_per_page, offset=offset
        )
        total_players = await self.get_total_players_with_achievements_count()
        embed = await info_embeds.format_achievement_stats_embed(stats, total_players, offset)
        view = PaginationView(
            criteria="achievements_stats",
            current_page=page,
            disable_first=not has_previous,
            disable_previous=not has_previous,
            disable_next=not has_next,
            disable_last=not has_next
        )
        return embed, [view] if view.children else []


achievement_service = AchievementService()
