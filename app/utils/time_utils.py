from datetime import datetime

import pytz

from app.config import config


class TimeUtils:
    @staticmethod
    async def get_current() -> datetime:
        return datetime.now(pytz.timezone(config.timezone))


time_utils = TimeUtils()
