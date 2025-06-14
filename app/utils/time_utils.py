from datetime import datetime

import pytz


class TimeUtils:
    @staticmethod
    async def get_current() -> datetime:
        return datetime.now(pytz.timezone("Europe/Kiev"))

    async def get_normalised(self) -> str:
        time_normalized = await self.get_current()
        return time_normalized.strftime("%H:%M:%S %d.%m.%Y")


time_utils = TimeUtils()
