import asyncio
from typing import Tuple

from disnake import User, Member, Embed
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.core.models import User as UserModel
from app.embeds import economy_embeds
from app.localization import t
from app.services import achievement_handler_service, economy_logging_service


class EconomyManagementService:
    @staticmethod
    async def update_user_balance(user: User, amount: int, reason: str, balance_only: bool = False) -> None:
        db_user, _ = await UserModel.get_or_create(user_id=user.id)

        await db_user.update_balance(amount, balance_only)

        asyncio.create_task(
            economy_logging_service.log_balance_change(
                user=user, amount=amount, new_balance=db_user.balance, reason=reason
            )
        )

        asyncio.create_task(achievement_handler_service.handle_economy_achievements(user))

    @staticmethod
    async def create_user_balance_message(user: User) -> Embed:
        db_user, is_created = await UserModel.get_or_create(user_id=user.id)
        higher_ranking_users_count = (
            await UserModel.filter(
                Q(reputation__gt=db_user.reputation)
                | Q(reputation=db_user.reputation, user_id__lt=db_user.user_id)
            ).count()
        )
        position = higher_ranking_users_count + 1

        return await economy_embeds.format_balance_embed(
            user.display_avatar.url, db_user.balance, db_user.reputation, position
        )

    @staticmethod
    async def reset_users_reputation() -> None:
        await UserModel.all().update(reputation=0)

    @staticmethod
    async def transfer_balance(sender: User | Member, receiver: User | Member, amount: int) -> Tuple[bool, str]:
        if sender.id == receiver.id:
            return False, t("errors.transfer_to_self")

        if not isinstance(receiver, (User, Member)) or receiver.bot:
            return False, t("errors.bots_not_allowed")

        if amount <= 0:
            return False, t("errors.transfer_amount_must_be_positive")

        async with in_transaction():
            db_sender, _ = await UserModel.get_or_create(user_id=sender.id)
            if db_sender.balance < amount:
                return False, t("errors.insufficient_funds_for_transfer", balance=db_sender.balance)

            db_receiver, _ = await UserModel.get_or_create(user_id=receiver.id)

            db_sender.balance -= amount
            await db_sender.save(update_fields=["balance"])

            db_receiver.balance += amount
            await db_receiver.save(update_fields=["balance"])

            asyncio.create_task(
                economy_logging_service.log_balance_change(
                    user=sender,
                    amount=-amount,
                    new_balance=db_sender.balance,
                    reason=t("economy.reasons.transfer_sent", user_id=receiver.id),
                )
            )

            asyncio.create_task(
                economy_logging_service.log_balance_change(
                    user=receiver,
                    amount=amount,
                    new_balance=db_receiver.balance,
                    reason=t("economy.reasons.transfer_received", user_id=sender.id),
                )
            )

        asyncio.create_task(achievement_handler_service.handle_economy_achievements(sender, amount_transferred=amount))
        asyncio.create_task(achievement_handler_service.handle_economy_achievements(receiver))

        return True, t("responses.transfer_success", amount=amount, user_id=receiver.id)


economy_management_service = EconomyManagementService()
