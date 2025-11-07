from typing import Set

from disnake import User
from tortoise.exceptions import DoesNotExist

from app.config import logger
from app.core.enums import ItemType
from app.core.models import (
    User as UserModel,
    SCPObject,
    Achievement,
    Item,
    UserAchievement,
    UserItem
)
from app.core.schemas import CrystallizationState, CoguardState
from app.utils.response_utils import response_utils


class AchievementHandlerService:
    @staticmethod
    async def _grant_achievement(user: User, achievement_id: str) -> None:
        try:
            db_user, _ = await UserModel.get_or_create(user_id=user.id)
            achievement = await Achievement.get(achievement_id=achievement_id)

            _, created = await UserAchievement.get_or_create(
                user=db_user, achievement=achievement
            )
            if created:
                logger.info(
                    f"Granted achievement '{achievement.name}' to user {user.id}"
                )
                await response_utils.send_dm_message(user, achievement)

        except DoesNotExist:
            logger.warning(
                f"Attempted to grant a non-existent "
                f"achievement with id: '{achievement_id}'"
            )
        except Exception as e:
            logger.error(
                f"Error granting achievement '{achievement_id}' "
                f"to user {user.id}: {e}"
            )

    @staticmethod
    async def _get_user_achievements_ids(user_id: int) -> Set[str]:
        db_user, _ = await UserModel.get_or_create(user_id=user_id)
        achievements = await UserAchievement.filter(
            user=db_user
        ).prefetch_related("achievement")
        return {ua.achievement.achievement_id for ua in achievements}

    async def handle_cooldown_achievement(self, user: User):
        achievements = await self._get_user_achievements_ids(user.id)
        if "workaholic" not in achievements:
            await self._grant_achievement(user, "workaholic")

    async def handle_view_card_achievements(self, user: User, target_user: User):
        achievements = await self._get_user_achievements_ids(user.id)

        if "welcome" not in achievements:
            await self._grant_achievement(user, "welcome")

        if user.id != target_user.id and "inspector" not in achievements:
            await self._grant_achievement(user, "inspector")

    async def handle_dossier_achievements(self, user: User):
        achievements = await self._get_user_achievements_ids(user.id)
        if "personal_file" not in achievements:
            await self._grant_achievement(user, "personal_file")

    async def handle_article_achievements(self, user: User, article: SCPObject):
        db_user, _ = await UserModel.get_or_create(user_id=user.id)
        achievements = await self._get_user_achievements_ids(user.id)

        viewed_count = await db_user.viewed_objects.all().count()

        if viewed_count >= 1 and "first_look" not in achievements:
            await self._grant_achievement(user, "first_look")
        if viewed_count >= 10 and "researcher" not in achievements:
            await self._grant_achievement(user, "researcher")
        if viewed_count >= 100 and "archivist" not in achievements:
            await self._grant_achievement(user, "archivist")

        if article.object_class == "keter" and "danger_face" not in achievements:
            await self._grant_achievement(user, "danger_face")
        if article.object_class == "thaumiel" and "thaumiel_secret" not in achievements:
            await self._grant_achievement(user, "thaumiel_secret")

    async def handle_work_achievements(
            self, user: User, is_risky: bool, is_success: bool
    ):
        achievements = await self._get_user_achievements_ids(user.id)

        if not is_risky and "first_paycheck" not in achievements:
            await self._grant_achievement(user, "first_paycheck")
        if is_risky and is_success and "risky_business" not in achievements:
            await self._grant_achievement(user, "risky_business")
        if is_risky and not is_success and "unlucky_adventurer" not in achievements:
            await self._grant_achievement(user, "unlucky_adventurer")

    async def handle_economy_achievements(
            self, user: User, amount_transferred: int = 0
    ):
        db_user, _ = await UserModel.get_or_create(user_id=user.id)
        achievements = await self._get_user_achievements_ids(user.id)

        if db_user.balance >= 1_000_000 and "balance_1m" not in achievements:
            await self._grant_achievement(user, "balance_1m")
        if db_user.reputation >= 100_000 and "reputation_100k" not in achievements:
            await self._grant_achievement(user, "reputation_100k")
        if db_user.reputation >= 1_000_000 and "reputation_1m" not in achievements:
            await self._grant_achievement(user, "reputation_1m")

        if amount_transferred > 10_000 and "philanthropist" not in achievements:
            await self._grant_achievement(user, "philanthropist")

    async def handle_crystallization_achievements(
            self, user: User, state: CrystallizationState, is_loss: bool
    ):
        achievements = await self._get_user_achievements_ids(user.id)
        if is_loss and "game_crystal_loss" not in achievements:
            await self._grant_achievement(user, "game_crystal_loss")
        if not is_loss and state.multiplier >= 2.5 and "game_crystal_win_x2.5" not in achievements:
            await self._grant_achievement(user, "game_crystal_win_x2.5")
        if not is_loss and (state.bet * state.multiplier) >= 50000 and "big_winner" not in achievements:
            await self._grant_achievement(user, "big_winner")

    async def handle_coin_flip_achievements(
            self, user: User, winnings: int
    ):
        achievements = await self._get_user_achievements_ids(user.id)
        if winnings >= 10000 and "game_coin_win_10_000" not in achievements:
            await self._grant_achievement(user, "game_coin_win_10_000")
        if winnings >= 50000 and "big_winner" not in achievements:
            await self._grant_achievement(user, "big_winner")

    async def handle_candy_achievements(
            self, user: User, player_taken: int, is_loss: bool
    ):
        achievements = await self._get_user_achievements_ids(user.id)
        if is_loss and "game_candy_loss" not in achievements:
            await self._grant_achievement(user, "game_candy_loss")
        if not is_loss and player_taken == 2 and "game_candy_win_2" not in achievements:
            await self._grant_achievement(user, "game_candy_win_2")

    async def handle_coguard_achievements(
            self, user: User, state: CoguardState, is_loss: bool
    ):
        achievements = await self._get_user_achievements_ids(user.id)
        if is_loss and state.win_streak == 0 and "game_coguard_loss_first" not in achievements:
            await self._grant_achievement(user, "game_coguard_loss_first")
        if not is_loss and state.win_streak >= 10 and "game_coguard_streak_10" not in achievements:
            await self._grant_achievement(user, "game_coguard_streak_10")
        if not is_loss and (state.bet * state.multiplier) >= 50000 and "big_winner" not in achievements:
            await self._grant_achievement(user, "big_winner")

    async def handle_hole_achievements(
            self, user: User, is_jackpot: bool, is_o5_win: bool, winnings: int
    ):
        achievements = await self._get_user_achievements_ids(user.id)
        if winnings > 0 and "game_hole_win" not in achievements:  # Проверяем, что есть выигрыш
            await self._grant_achievement(user, "game_hole_win")
        if is_jackpot and "game_hole_jackpot" not in achievements:
            await self._grant_achievement(user, "game_hole_jackpot")
        if is_o5_win and "game_hole_o5_win" not in achievements:
            await self._grant_achievement(user, "game_hole_o5_win")
        if winnings >= 50000 and "big_winner" not in achievements:
            await self._grant_achievement(user, "big_winner")

    async def handle_scp173_achievements(
            self, user: User, is_host: bool, is_survivor: bool, is_first_death: bool, pot: int = 0
    ):
        achievements = await self._get_user_achievements_ids(user.id)
        if is_host and "game_scp173_host" not in achievements:
            await self._grant_achievement(user, "game_scp173_host")
        if is_survivor and "game_scp173_survivor" not in achievements:
            await self._grant_achievement(user, "game_scp173_survivor")
        if is_first_death and "game_scp173_first_death" not in achievements:
            await self._grant_achievement(user, "game_scp173_first_death")
        if pot >= 50000 and "big_winner" not in achievements:
            await self._grant_achievement(user, "big_winner")

    async def handle_shop_achievements(self, user: User, bought_item_id: str):
        db_user, _ = await UserModel.get_or_create(user_id=user.id)
        achievements = await self._get_user_achievements_ids(user.id)

        if "first_purchase" not in achievements:
            await self._grant_achievement(user, "first_purchase")

        card_count = await UserItem.filter(user=db_user, item__item_type=ItemType.CARD).count()
        if card_count >= 5 and "card_collector" not in achievements:
            await self._grant_achievement(user, "card_collector")

        purchasable_card_ids = set(
            await Item.filter(
                item_type=ItemType.CARD, price__gt=0
            ).values_list("item_id", flat=True)
        )
        user_cards = await UserItem.filter(
            user=db_user, item__item_type=ItemType.CARD
        ).prefetch_related("item")
        user_card_ids = {uc.item.item_id for uc in user_cards}

        if purchasable_card_ids.issubset(
                user_card_ids
        ) and "access_master" not in achievements:
            await self._grant_achievement(user, "access_master")

        achievements_map = {
            "keycard_scientist": "scientist_promotion",
            "keycard_major_scientist": "major_scientist_promotion",
            "keycard_engineering": "engineer_promotion",
            "keycard_zone_manager": "upcoming_promotion",
            "keycard_security": "security_promotion",
            "keycard_sergeant_mog": "sergeant_promotion",
            "keycard_lieutenant_mog": "lieutenant_promotion",
            "keycard_captain_mog": "upcoming_promotion",
            "keycard_zone_director": "zone_authority",
            "keycard_o5": "o5_council",
            "keycard_redacted": "administrator_presence"
        }
        if bought_item_id in achievements_map and achievements_map[bought_item_id] not in achievements:
            await self._grant_achievement(user, achievements_map[bought_item_id])


achievement_handler_service = AchievementHandlerService()
