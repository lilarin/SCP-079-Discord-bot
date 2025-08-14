from typing import Tuple

from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.core.models import User
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

    @staticmethod
    async def transfer_balance(sender_id: int, receiver_id: int, amount: int) -> Tuple[bool, str]:
        if sender_id == receiver_id:
            return False, "Ви не можете переказати кошти самому собі"

        if amount <= 0:
            return False, "Сума переводу повинна бути більше нуля"

        async with in_transaction():
            sender, _ = await User.get_or_create(user_id=sender_id)
            if sender.balance < amount:
                return False, (
                    "У вас недостатньо коштів для переказу\n"
                    f"-# Поточний баланс – {sender.balance} 💠"
                )

            receiver, _ = await User.get_or_create(user_id=receiver_id)

            sender.balance -= amount
            await sender.save(update_fields=["balance"])

            receiver.balance += amount
            await receiver.save(update_fields=["balance"])

        return True, f"Ви успішно переказали {amount} 💠 користувачу <@{receiver_id}>"


economy_management_service = EconomyManagementService()
