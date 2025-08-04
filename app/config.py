import logging
import logging.handlers
import os
import queue
import sys
from dataclasses import dataclass
from typing import List, Dict, Tuple
from urllib.parse import urlparse

from PIL import Image, ImageFont
from dotenv import load_dotenv


@dataclass
class TemplateConfig:
    image: Image.Image
    primary_color: int
    secondary_color: int
    embed_color: int


class Config:
    def __init__(self):
        load_dotenv()

        # General settings
        self.discord_bot_token = self._get_env_variable("DISCORD_BOT_TOKEN")
        self.database_url = self._get_env_variable("SUPABASE_DIRECT_URL")
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # SCP articles settings
        self.scp_classes = {
            "Безпечний": "safe",
            "Евклід": "euclid",
            "Кетер": "keter",
            "Тауміель": "thaumiel",
            "Особливий": "exotic",
            "Метаклас": "meta",
        }
        self.scp_class_config = {
            None: ("#AAAAAA", "📁"),
            "safe": ("#6AAB64", "📗"),
            "euclid": ("#FF9F52", "📙"),
            "keter": ("#E13821", "📕"),
            "thaumiel": ("#222222", "📓"),
            "exotic": ("#D74D97", "📔"),
            "meta": ("#326D9E", "📘")
        }
        self.scp_ranges = {
            "001-999": "1",
            "1000-1999": "2",
            "2000-2999": "3",
            "3000-3999": "4",
            "4000-4999": "5",
            "5000-5999": "6",
            "6000-6999": "7",
            "7000-7999": "8",
            "8000-8999": "9",
        }
        self.wiki_url = "http://scp-ukrainian.wikidot.com"
        self.scrape_urls = [
            f"{self.wiki_url}/scp-series-ua",
            f"{self.wiki_url}/scp-series",
            f"{self.wiki_url}/scp-series-2",
            f"{self.wiki_url}/scp-series-3",
            f"{self.wiki_url}/scp-series-4",
            f"{self.wiki_url}/scp-series-5",
            f"{self.wiki_url}/scp-series-6",
            f"{self.wiki_url}/scp-series-7",
            f"{self.wiki_url}/scp-series-8",
            f"{self.wiki_url}/scp-series-9"
        ]

        # Leaderboard settings
        self.leaderboard_options = {
            "Переглянуті статті": "articles",
            "Баланс": "balance",
            "Репутація": "reputation"
        }

        # Articles settings
        self.article_template_path = os.path.join(self.project_root, "assets", "articles", "article.png")
        self.primary_font_path = os.path.join(self.project_root, "assets", "fonts", "BauhausDemi.ttf")
        self.secondary_font_path = os.path.join(self.project_root, "assets", "fonts", "Inter_18pt-Bold.ttf")
        self.fonts: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}
        self.templates: List[TemplateConfig] = self._load_templates()

    def get_font(self, font_path: str, size: int) -> ImageFont.FreeTypeFont:
        if (font_path, size) not in self.fonts:
            self.fonts[(font_path, size)] = ImageFont.truetype(font_path, size=size)
        return self.fonts[(font_path, size)]

    @staticmethod
    def _get_env_variable(var_name: str) -> str | None:
        value = os.environ.get(var_name)
        if not value:
            logger.error(f"{var_name} environment variable is not set!")
            return None
        return value

    def _load_templates(self) -> List[TemplateConfig]:
        base_path = str(os.path.join(self.project_root, "assets", "cards"))
        template_configs = [
            {
                "path": os.path.join(base_path, "keycard-1.png"),
                "primary": "#FBFBFB",
                "secondary": "#A6A6A6",
                "embed": "#0D0D0D"
            },
            {
                "path": os.path.join(base_path, "keycard-2.png"),
                "primary": "#343434",
                "secondary": "#717171",
                "embed": "#FBFBFB"
            },
            {
                "path": os.path.join(base_path, "keycard-3.png"),
                "primary": "#FFE2E2",
                "secondary": "#E89495",
                "embed": "#730004"
            },
            {
                "path": os.path.join(base_path, "keycard-4.png"),
                "primary": "#C4E4FF",
                "secondary": "#80BFFF",
                "embed": "#1B2C86"
            },
            {
                "path": os.path.join(base_path, "keycard-5.png"),
                "primary": "#3E41E0",
                "secondary": "#5265FC",
                "embed": "#4BA3F5"
            },
            {
                "path": os.path.join(base_path, "keycard-6.png"),
                "primary": "#4BA3F5",
                "secondary": "#70BBFF",
                "embed": "#ABD6FF"
            },
            {
                "path": os.path.join(base_path, "keycard-7.png"),
                "primary": "#2E2E2E",
                "secondary": "#4F4F4F",
                "embed": "#808080"
            },
            {
                "path": os.path.join(base_path, "keycard-8.png"),
                "primary": "#8BF3E8",
                "secondary": "#13C5B3",
                "embed": "#258F84"
            },
            {
                "path": os.path.join(base_path, "keycard-9.png"),
                "primary": "#FFC2BA",
                "secondary": "#E1A597",
                "embed": "#BB8D83"
            },
            {
                "path": os.path.join(base_path, "keycard-10.png"),
                "primary": "#2E2E2E",
                "secondary": "#717171",
                "embed": "#FFC74B"
            },
            {
                "path": os.path.join(base_path, "keycard-11.png"),
                "primary": "#484844",
                "secondary": "#858585",
                "embed": "#FFE18C"
            },
            {
                "path": os.path.join(base_path, "keycard-12.png"),
                "primary": "#F0EBFF",
                "secondary": "#A287FF",
                "embed": "#BEB3E6"
            },
        ]
        return [
            TemplateConfig(
                image=Image.open(conf["path"]),
                primary_color=int(conf["primary"].lstrip('#'), 16),
                secondary_color=int(conf["secondary"].lstrip('#'), 16),
                embed_color=int(conf["embed"].lstrip('#'), 16)
            ) for conf in template_configs
        ]

    @staticmethod
    def setup_logging():
        log_queue = queue.Queue(-1)

        queue_handler = logging.handlers.QueueHandler(log_queue)

        logger = logging.getLogger("scp-profiles")
        logger.setLevel(logging.INFO)
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

        return logger, listener


config = Config()
logger, log_listener = config.setup_logging()


# Tortoise ORM Settings
db_url = urlparse(config.database_url)
tortoise_orm = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": db_url.hostname,
                "port": db_url.port,
                "user": db_url.username,
                "password": db_url.password,
                "database": db_url.path[1:],
                "statement_cache_size": 0,
            },
        }
    },
    "apps": {
        "models": {
            "models": ["app.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
