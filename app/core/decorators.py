from functools import wraps

from app.core.models import User
from app.localization import t
from app.services.economy_management_service import economy_management_service
from app.utils.response_utils import response_utils


def target_is_user(func):
    @wraps(func)
    async def wrapper(interaction, *args, **kwargs):
        user = kwargs.get("user")
        if user and user.bot:
            await response_utils.send_ephemeral_response(interaction, message=t("errors.bots_not_allowed"))
            return

        await func(interaction, *args, **kwargs)

    return wrapper


def remove_bet_from_balance(func):
    @wraps(func)
    async def wrapper(interaction, *args, **kwargs):
        bet = kwargs.get("bet")

        await response_utils.wait_for_response(interaction)
        if bet <= 0:
            await response_utils.send_response(
                interaction, message=t("errors.bet_must_be_positive"), delete_after=10
            )
            return

        db_user, _ = await User.get_or_create(user_id=interaction.user.id)

        if db_user.balance < bet:
            await response_utils.send_response(
                interaction, t("errors.insufficient_funds_for_bet", balance=db_user.balance), delete_after=10,
            )
            return

        reason = t("economy.reasons.game_bet", game_name=interaction.application_command.name)
        await economy_management_service.update_user_balance(interaction.user, -bet, reason=reason)

        await func(interaction, *args, **kwargs)

    return wrapper
