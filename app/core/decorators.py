from functools import wraps

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