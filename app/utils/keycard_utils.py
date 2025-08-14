from io import BytesIO
from typing import Tuple

from disnake import User, Member


class KeyCardUtils:
    @staticmethod
    async def process_username(user_name: str) -> str:
        user_name = user_name.upper()
        if len(user_name) > 14:
            user_name = (user_name[:12].strip() + "..")
        return user_name

    @staticmethod
    async def get_user_code(timestamp: float) -> str:
        return "-".join(str(round(timestamp, 1)).split("."))

    async def collect_user_data(self, user: User | Member) -> Tuple[int, str, str, BytesIO, BytesIO]:
        try:
            user_code = await self.get_user_code(user.joined_at.timestamp())
        except AttributeError:
            user_code = ""

        user_name = await self.process_username(user.display_name)

        avatar = BytesIO(await user.avatar.read())

        avatar_decoration = user.avatar_decoration
        if avatar_decoration:
            avatar_decoration = BytesIO(await avatar_decoration.read())

        return user.id, user_name, user_code, avatar, avatar_decoration


keycard_utils = KeyCardUtils()
