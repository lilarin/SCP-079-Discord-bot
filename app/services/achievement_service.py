from typing import Dict, List, Tuple, Optional

from disnake import Embed, Component, User
from tortoise.functions import Count

from app.config import config, logger
from app.core.models import Achievement, User as UserModel
from app.core.schemas import AchievementConfig
from app.utils.ui_utils import ui_utils


class AchievementService:
    def __init__(self):
        self.achievements_config: Dict[str, AchievementConfig] = config.achievements

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
        achievements_query = db_user.achievements.all().order_by("id").offset(offset).limit(limit + 1)
        achievements_raw = await achievements_query

        has_next = len(achievements_raw) > limit
        current_page_items = achievements_raw[:limit]
        has_previous = offset > 0

        return current_page_items, has_previous, has_next

    @staticmethod
    async def get_total_user_achievements_count(user_id: int) -> int:
        user, _ = await UserModel.get_or_create(user_id=user_id)
        return await user.achievements.all().count()

    async def init_achievements_message(self, user: User) -> Optional[Tuple[Embed, List[Component]]]:
        db_user, _ = await UserModel.get_or_create(user_id=user.id)
        items, _, has_next = await self._get_paginated_user_achievements(
            user_id=user.id, limit=config.achievements_per_page
        )

        embed = await ui_utils.format_achievements_embed(user, items)

        components = await ui_utils.init_control_buttons(
            criteria="achievements",
            disable_first_page_button=True,
            disable_previous_page_button=True,
            disable_next_page_button=not has_next,
            disable_last_page_button=not has_next,
            target_user_id=user.id
        )
        return embed, components

    async def edit_achievements_message(
            self, user: User, page: int, offset: int
    ) -> Optional[Tuple[Embed, List[Component]]]:
        items, has_previous, has_next = await self._get_paginated_user_achievements(
            user_id=user.id, limit=config.achievements_per_page, offset=offset
        )

        embed = await ui_utils.format_achievements_embed(user, items, offset=offset)

        components = await ui_utils.init_control_buttons(
            criteria="achievements",
            current_page_text=page,
            disable_first_page_button=not has_previous,
            disable_previous_page_button=not has_previous,
            disable_next_page_button=not has_next,
            disable_last_page_button=not has_next,
            target_user_id=user.id
        )
        return embed, components

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
        return await UserModel.annotate(ach_count=Count("achievements")).filter(ach_count__gt=0).count()

    @staticmethod
    async def get_total_achievements_count() -> int:
        return await Achievement.all().count()

    async def init_stats_message(self) -> Optional[Tuple[Embed, List[Component]]]:
        stats, _, has_next = await self.get_achievements_statistics(
            limit=config.achievements_per_page
        )
        total_players = await self.get_total_players_with_achievements_count()

        embed = await ui_utils.format_achievement_stats_embed(stats, total_players)

        components = await ui_utils.init_control_buttons(
            criteria="achievements_stats",
            disable_first_page_button=True,
            disable_previous_page_button=True,
            disable_next_page_button=not has_next,
            disable_last_page_button=not has_next
        )
        return embed, components

    async def edit_stats_message(self, page: int, offset: int) -> Optional[Tuple[Embed, List[Component]]]:
        stats, has_previous, has_next = await self.get_achievements_statistics(
            limit=config.achievements_per_page, offset=offset
        )
        total_players = await self.get_total_players_with_achievements_count()

        embed = await ui_utils.format_achievement_stats_embed(stats, total_players, offset)

        components = await ui_utils.init_control_buttons(
            criteria="achievements_stats",
            current_page_text=page,
            disable_first_page_button=not has_previous,
            disable_previous_page_button=not has_previous,
            disable_next_page_button=not has_next,
            disable_last_page_button=not has_next
        )
        return embed, components


achievement_service = AchievementService()
