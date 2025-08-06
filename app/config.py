import json
import logging
import logging.handlers
import os
import queue
import sys
from typing import Dict, Tuple, Optional
from urllib.parse import urlparse

from PIL import Image, ImageFont
from dotenv import load_dotenv

from app.core.schemas import CardConfig, WorkPrompts, NonLegalPrompts


class Config:
    def __init__(self):
        load_dotenv()

        # Core Application Settings
        self.discord_bot_token = self._get_env_variable("DISCORD_BOT_TOKEN")
        self.database_url = self._get_env_variable("SUPABASE_DIRECT_URL")
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # File System Paths
        self.assets_dir_path = os.path.join(self.project_root, "assets")
        self.cards_dir_path = os.path.join(self.assets_dir_path, "cards")
        self.shop_cards_path = os.path.join(self.assets_dir_path, "configs", "shop_cards.json")
        self.work_prompts_path = os.path.join(self.assets_dir_path, "configs", "work_prompts.json")
        self.article_template_path = os.path.join(self.assets_dir_path, "articles", "article.png")
        self.primary_font_path = os.path.join(self.assets_dir_path, "fonts", "BauhausDemi.ttf")
        self.secondary_font_path = os.path.join(self.assets_dir_path, "fonts", "Inter_18pt-Bold.ttf")

        # Image, card and work prompts Configuration
        self.fonts: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}
        self.cards: Dict[str, CardConfig] = self._load_cards_from_json()
        self.work_prompts: Dict[str, WorkPrompts] = self._load_work_prompts_from_json()

        # SCP Article Scraper Settings
        self.wiki_url = "http://scp-ukrainian.wikidot.com"
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
        self.scrape_urls = [
            f"{self.wiki_url}/scp-series-ua", f"{self.wiki_url}/scp-series", f"{self.wiki_url}/scp-series-2",
            f"{self.wiki_url}/scp-series-3", f"{self.wiki_url}/scp-series-4", f"{self.wiki_url}/scp-series-5",
            f"{self.wiki_url}/scp-series-6", f"{self.wiki_url}/scp-series-7", f"{self.wiki_url}/scp-series-8",
            f"{self.wiki_url}/scp-series-9"
        ]

        # UI & Pagination Settings
        self.leaderboard_options = {
            "Переглянуті статті": "articles",
            "Баланс": "balance",
            "Репутація": "reputation"
        }
        self.leaderboard_items_per_page = 10
        self.shop_items_per_page = 4
        self.inventory_items_per_page = 5

    def get_font(self, font_path: str, size: int) -> ImageFont.FreeTypeFont:
        if (font_path, size) not in self.fonts:
            self.fonts[(font_path, size)] = ImageFont.truetype(font_path, size=size)
        return self.fonts[(font_path, size)]

    @staticmethod
    def _get_env_variable(var_name: str) -> str:
        value = os.environ.get(var_name)
        if not value:
            logger.error(f"{var_name} environment variable is not set!")
            exit(1)
        return value

    def _load_cards_from_json(self) -> Optional[Dict[str, CardConfig]]:
        """Loads card configurations from a JSON file."""
        try:
            with open(self.shop_cards_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            loaded_cards: Dict[str, CardConfig] = {}
            for key, data in raw_data.items():
                full_image_path = os.path.join(self.cards_dir_path, data["image_file"])
                loaded_cards[key] = CardConfig(
                    name=data["name"],
                    description=data["description"],
                    price=data["price"],
                    quantity_range=tuple(data["quantity_range"]),
                    image=Image.open(full_image_path),
                    primary_color=int(data["colors"]["primary"].lstrip("#"), 16),
                    secondary_color=int(data["colors"]["secondary"].lstrip("#"), 16),
                    embed_color=int(data["colors"]["embed"].lstrip("#"), 16)
                )
            logging.info(f"Successfully loaded {len(loaded_cards)} card configurations from JSON.")
            return loaded_cards

        except FileNotFoundError:
            logging.error(f"Card config file not found at {self.shop_cards_path}")
            exit(1)
        except json.JSONDecodeError:
            logging.error(f"Could not decode JSON from {self.shop_cards_path}. Check for syntax errors.")
            exit(1)
        except KeyError as e:
            logging.error(f"Missing key in card data from {self.shop_cards_path}: {e}")
            exit(1)

    def _load_work_prompts_from_json(self) -> Optional[Dict[str, WorkPrompts]]:
        """Loads work prompt configurations from a JSON file."""
        try:
            with open(self.work_prompts_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            loaded_prompts: Dict[str, WorkPrompts] = {}
            for key, data in raw_data.items():
                non_legal_data = data["non-legal"]
                non_legal_prompts_obj = NonLegalPrompts(
                    success=non_legal_data["success"],
                    failure=non_legal_data["failure"]
                )

                loaded_prompts[key] = WorkPrompts(
                    legal=data["legal"],
                    non_legal=non_legal_prompts_obj
                )
            logging.info(f"Successfully loaded {len(loaded_prompts)} work prompt configurations from JSON.")
            return loaded_prompts

        except FileNotFoundError:
            logging.error(f"Work prompts config file not found at {self.work_prompts_path}")
            exit(1)
        except json.JSONDecodeError:
            logging.error(f"Could not decode JSON from {self.work_prompts_path}. Check for syntax errors.")
            exit(1)
        except KeyError as e:
            logging.error(f"Missing key in work prompts data from {self.work_prompts_path}: {e}")
            exit(1)

    @staticmethod
    def setup_logging():
        log_queue = queue.Queue(-1)

        queue_handler = logging.handlers.QueueHandler(log_queue)

        logger = logging.getLogger("scp-profiles")
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

        return logger, listener


# Initialize Config and Logging
config = Config()
logger, log_listener = config.setup_logging()

# Tortoise ORM Settings
# Used directly by the ORM initialization.
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
            "models": ["app.core.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
