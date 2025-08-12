from functools import wraps

from app.core.models import User
from app.services.economy_management_service import economy_management_service
from app.utils.response_utils import response_utils


def target_is_user(func):
    @wraps(func)
    async def wrapper(interaction, *args, **kwargs):

        user = kwargs.get("user")
        if user and user.bot:
            await response_utils.send_ephemeral_response(
                interaction, message="Команду не можна використовувати на ботах"
            )
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
                interaction, message="Ставка має бути більше нуля", delete_after=5
            )
            return

        db_user, _ = await User.get_or_create(user_id=interaction.user.id)

        if db_user.balance < bet:
            await response_utils.send_response(
                interaction, "У вас недостатньо коштів для цієї ставки", delete_after=5
            )
            return

        await economy_management_service.update_user_balance(interaction.user.id, -bet)

        await func(interaction, *args, **kwargs)

    return wrapper