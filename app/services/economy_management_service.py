from typing import Tuple

from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q

from app.models import User
from app.utils.ui_utils import ui_utils


class EconomyManagementService:
    @staticmethod
    async def set_user_balance(user_id: int, amount: int) -> None:
        user, is_created = await User.get_or_create(user_id=user_id)
        if not user:
            raise DoesNotExist(f"Користувача з ID {user_id} не знайдено")
        await user.set_balance(amount)

    @staticmethod
    async def set_user_reputation(user_id: int, amount: int) -> None:
        user, is_created = await User.get_or_create(user_id=user_id)
        if not user:
            raise DoesNotExist(f"Користувача з ID {user_id} не знайдено")
        await user.set_reputation(amount)

    @staticmethod
    async def update_user_balance(user_id: int, amount: int) -> None:
        user, is_created = await User.get_or_create(user_id=user_id)
        if not user:
            raise DoesNotExist(f"Користувача з ID {user_id} не знайдено")
        await user.update_balance(amount)

    @staticmethod
    async def create_user_balance_message(user_id: int) -> Tuple[int, int]:
        user, is_created = await User.get_or_create(user_id=user_id)
        higher_ranking_users_count = await User.filter(
            Q(reputation__gt=user.reputation) |
            Q(reputation=user.reputation, user_id__lt=user.user_id)
        ).count()
        position = higher_ranking_users_count + 1

        return await ui_utils.format_balance_embed(user.balance, user.reputation, position)

    @staticmethod
    async def reset_users_reputation() -> None:
        await User.all().update(reputation=0)


economy_management_service = EconomyManagementService()
