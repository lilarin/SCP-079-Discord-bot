import asyncio

from tortoise import Tortoise

from app.bot import bot
from app.config import logger, config, log_listener, tortoise_orm

if __name__ == "__main__":
    try:
        logger.info("Starting bot...")
        log_listener.start()
        asyncio.run(Tortoise.init(tortoise_orm))
        logger.info("Tortoise-ORM started.")
        bot.run(config.discord_bot_token)
    finally:
        asyncio.run(Tortoise.close_connections())
        logger.info("Tortoise-ORM connections closed.")
