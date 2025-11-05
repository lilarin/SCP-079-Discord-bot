import logging
import logging.handlers
import os
import queue
import sys
from urllib.parse import urlparse, ParseResult

from dotenv import load_dotenv


class Config:
    def __init__(self):
        load_dotenv()

        # Core Application configuration
        self.discord_bot_token: str = self._get_env_variable("DISCORD_BOT_TOKEN")
        self.economy_logging_channel_id: int = int(self._get_env_variable("ECONOMY_LOGGING_CHANNEL_ID"))
        self.database_url: ParseResult = urlparse(self._get_env_variable("DATABASE_DIRECT_URL"))
        self.update_scp_objects: bool = "True" == self._get_env_variable("UPDATE_SCP_OBJECTS")
        self.sync_shop_cards: bool = "True" == self._get_env_variable("SYNC_SHOP_CARDS")
        self.sync_achievements: bool = "True" == self._get_env_variable("SYNC_ACHIEVEMENTS")
        self.timezone: str = "Europe/Kiev"
        self.administrator_user_ids = [354638720600768522]

        # Tortoise ORM configuration
        self.tortoise_settings = {
            "connections": {
                "default": {
                    "engine": "tortoise.backends.asyncpg",
                    "credentials": {
                        "host": self.database_url.hostname,
                        "port": self.database_url.port,
                        "user": self.database_url.username,
                        "password": self.database_url.password,
                        "database": self.database_url.path[1:],
                        "statement_cache_size": 0,
                    },
                }
            },
            "apps": {
                "models": {
                    "models": ["app.core.models", "aerich.models"],
                    "default_connection": "default",
                },
            },
        }

    @staticmethod
    def _get_env_variable(var_name: str) -> str:
        value = os.environ.get(var_name)
        if not value:
            logging.error(f"{var_name} environment variable is not set!")
            exit(1)
        return value

    @staticmethod
    def setup_logging():
        log_queue = queue.Queue(-1)

        queue_handler = logging.handlers.QueueHandler(log_queue)

        logger = logging.getLogger("scp-079-bot")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.addHandler(queue_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(levelname)s:     [%(asctime)s] %(name)s - %(message)s",
            datefmt="%H:%M:%S %d.%m.%Y"
        )
        console_handler.setFormatter(formatter)

        listener = logging.handlers.QueueListener(
            log_queue, console_handler, respect_handler_level=True
        )

        listener.start()

        return logger


# Initialize Config and Logging
config = Config()
tortoise_orm = config.tortoise_settings
logger = config.setup_logging()
