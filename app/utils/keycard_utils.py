from disnake import Embed


class KeyCardUtils:
    @staticmethod
    async def process_username(user_name):
        user_name = user_name.upper()
        if len(user_name) > 14:
            user_name = (user_name[:12].strip() + "..")
        return user_name

    @staticmethod
    async def get_user_code(timestamp: float):
        return "-".join(str(round(timestamp, 1)).split("."))

    @staticmethod
    async def format_new_user_embed(user_mention, card, color):
        embed = Embed(
            description=f"Вітаємо {user_mention} у складі співробітників фонду!",
            color=color
        )
        embed.set_image(file=card)
        return embed

    @staticmethod
    async def format_user_embed(card, color):
        embed = Embed(
            title="Інформація про співробітника фонду",
            color=color
        )
        embed.set_image(file=card)
        return embed


keycard_utils = KeyCardUtils()
