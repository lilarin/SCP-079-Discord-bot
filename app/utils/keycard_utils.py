import re
from io import BytesIO
from typing import Tuple, Optional

from disnake import User, Member


class KeyCardUtils:
    @staticmethod
    async def process_username(user_name: str) -> str:
        processed_name = re.sub(r'\[.*?\]|\(.*?\)|\{.*?\}', '', user_name).strip()
        if processed_name:
            user_name = processed_name

        user_name = re.sub(r'[^a-zA-Zа-яА-Я0-9\s._\-]', '', user_name)
        user_name = re.sub(r'\s+', ' ', user_name).strip()

        user_name = user_name.upper()
        if len(user_name) > 14:
            user_name = (user_name[:12].strip() + "..")
        return user_name

    @staticmethod
    async def get_user_code(timestamp: float) -> str:
        return "-".join(str(round(timestamp, 1)).split("."))

    async def collect_user_data(
            self, user: User | Member
    ) -> Tuple[int, str, str, BytesIO, str, Optional[BytesIO], Optional[str]]:
        try:
            user_code = await self.get_user_code(user.joined_at.timestamp())
        except AttributeError:
            user_code = ""

        user_name = await self.process_username(user.display_name)

        if isinstance(user, User):
            avatar = user.avatar
        elif isinstance(user, Member):
            avatar = user.display_avatar
        else:
            avatar = user.default_avatar

        avatar_bytes = BytesIO(await avatar.read())
        avatar_key = avatar.key

        avatar_decoration = user.avatar_decoration
        avatar_decoration_bytes = None
        avatar_decoration_key = None
        if avatar_decoration:
            avatar_decoration_bytes = BytesIO(await avatar_decoration.read())
            avatar_decoration_key = avatar_decoration.key

        return user.id, user_name, user_code, avatar_bytes, avatar_key, avatar_decoration_bytes, avatar_decoration_key


keycard_utils = KeyCardUtils()
