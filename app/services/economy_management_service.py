from typing import Tuple

from tortoise.exceptions import DoesNotExist

from app.models import User
from app.utils.economy_management_utils import economy_management_utils


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
        position = await User.filter(reputation__gt=user.reputation).count() + 1 if user.reputation > 0 else None

        return await economy_management_utils.format_balance_embed(user.balance, user.reputation, position)


economy_management_service = EconomyManagementService()
