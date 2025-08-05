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


keycard_utils = KeyCardUtils()
