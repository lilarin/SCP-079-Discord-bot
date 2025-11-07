import asyncio
import re
from typing import Optional

from disnake import User, Member, TextChannel
from disnake.ext.commands import InteractionBot

from app.config import config, logger
from app.embeds import economy_embeds
from app.utils.response_utils import response_utils


class EconomyLoggingService:
    def __init__(self):
        self._bot: Optional[InteractionBot] = None
        self._channel: Optional[TextChannel] = None
        self._counter: int = 0
        self._lock = asyncio.Lock()

    async def init_logging(self, bot: InteractionBot):
        logger.info("Starting economy logging initialization..")
        self._bot = bot

        log_channel = await self._get_channel()
        if not log_channel:
            logger.warning("Log channel not found. Counter starts from 0")
            return

        async for message in log_channel.history(limit=100):
            if message.author.id == self._bot.user.id and message.embeds:
                footer_text = message.embeds[0].footer.text
                if footer_text and footer_text.startswith("#"):
                    try:
                        last_id = int(re.search(r'\d+', footer_text).group())
                        self._counter = last_id
                        logger.info(f"Successfully loaded last log ID: {self._counter}")
                        return
                    except (ValueError, AttributeError):
                        continue

        logger.info("No previous logs found in the channel. Counter starts from 0")

    async def get_next(self) -> int:
        async with self._lock:
            self._counter += 1
            return self._counter

    async def _get_channel(self) -> Optional[TextChannel]:
        if self._channel is None:
            if not self._bot:
                logger.error("Couldn't get economy logging channel because bot is not initialized!")
                return None

            channel = self._bot.get_channel(config.economy_logging_channel_id)
            if isinstance(channel, TextChannel):
                self._channel = channel
                logger.info(f"Logging to {channel.name}")
            else:
                logger.error(f"Channel with ID {config.economy_logging_channel_id} is not a TextChannel or not found!")
        return self._channel

    async def log_balance_change(
            self, user: User | Member, amount: int, new_balance: int, reason: str
    ) -> None:
        if not self._bot:
            return

        log_channel = await self._get_channel()
        if not log_channel:
            return

        user_mention = f"<@{user.id}>"
        log_id = await self.get_next()

        embed = await economy_embeds.format_balance_log_embed(
            user_mention=user_mention,
            avatar_url=user.display_avatar.url,
            amount=amount,
            new_balance=new_balance,
            reason=reason,
            log_id=log_id
        )

        await response_utils.send_new_message(log_channel, embed=embed)


economy_logging_service = EconomyLoggingService()
