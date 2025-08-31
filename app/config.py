import logging
import logging.handlers
import os
import queue
import sys
from typing import Dict, Tuple, Optional, List
from urllib.parse import urlparse

from PIL import ImageFont
from disnake.ext.commands import BucketType
from dotenv import load_dotenv

from app.core.schemas import CardConfig, WorkPrompts, AchievementConfig
from app.utils.configs_load_utils import configs_load_utils


class Config:
    def __init__(self):
        load_dotenv()

        # Core Application configuration
        self.discord_bot_token: str = self._get_env_variable("DISCORD_BOT_TOKEN")
        self.economy_logging_channel_id: int = int(self._get_env_variable("ECONOMY_LOGGING_CHANNEL_ID"))
        self.database_url: str = self._get_env_variable("SUPABASE_DIRECT_URL")
        self.update_scp_objects: bool = "True" == self._get_env_variable("UPDATE_SCP_OBJECTS")
        self.sync_shop_cards: bool = "True" == self._get_env_variable("SYNC_SHOP_CARDS")
        self.sync_achievements: bool = "True" == self._get_env_variable("SYNC_ACHIEVEMENTS")
        self.project_root: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.timezone: str = "Europe/Kiev"

        # File System Paths configuration
        self.assets_dir_path: str = os.path.join(self.project_root, "assets")
        self.cards_dir_path: str = os.path.join(self.assets_dir_path, "cards")
        self.shop_cards_path: str = os.path.join(self.assets_dir_path, "configs", "shop_cards.json")
        self.work_prompts_path: str = os.path.join(self.assets_dir_path, "configs", "work_prompts.json")
        self.achievements_config_path: str = os.path.join(self.assets_dir_path, "configs", "achievements.json")
        self.article_template_path: str = os.path.join(self.assets_dir_path, "articles", "article.png")
        self.primary_font_path: str = os.path.join(self.assets_dir_path, "fonts", "BauhausDemi.ttf")
        self.secondary_font_path: str = os.path.join(self.assets_dir_path, "fonts", "Inter_18pt-Bold.ttf")

        # Image, card and work prompts configuration
        self.fonts: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}
        self.cards: Dict[str, CardConfig] = configs_load_utils.load_cards_from_json(self.shop_cards_path, self.cards_dir_path)
        self.work_prompts: Dict[str, WorkPrompts] = configs_load_utils.load_work_prompts_from_json(self.work_prompts_path)
        self.achievements: Dict[str, AchievementConfig] = configs_load_utils.load_achievements_from_json(self.achievements_config_path)

        # SCP Article Scraper configuration
        self.wiki_url: str = "http://scp-ukrainian.wikidot.com"
        self.scp_classes: Dict[str, str] = {
            "Безпечний": "safe",
            "Евклід": "euclid",
            "Кетер": "keter",
            "Тауміель": "thaumiel",
            "Особливий": "exotic",
            "Метаклас": "meta",
        }
        self.scp_class_config: Dict[Optional[str], Tuple[str, str]] = {
            None: ("#AAAAAA", "📁"),
            "safe": ("#6AAB64", "📗"),
            "euclid": ("#FF9F52", "📙"),
            "keter": ("#E13821", "📕"),
            "thaumiel": ("#222222", "📓"),
            "exotic": ("#D74D97", "📔"),
            "meta": ("#326D9E", "📘")
        }
        self.scp_ranges: Dict[str, str] = {
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
        self.scrape_urls: List[str] = [
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

        # UI & Pagination configuration
        self.leaderboard_options: Dict[str, str] = {
            "Переглянуті статті": "articles",
            "Баланс": "balance",
            "Репутація": "reputation",
            "Досягнення": "achievements"
        }
        self.leaderboard_items_per_page: int = 10
        self.shop_items_per_page: int = 3
        self.inventory_items_per_page: int = 5
        self.achievements_per_page: int = 7

        # Economy configuration
        self.legal_work_reward_range: Tuple[int, int] = (50, 150)
        self.non_legal_work_success_chance: float = 0.5
        self.non_legal_work_reward_range: Tuple[int, int] = (200, 500)
        self.non_legal_work_penalty_range: Tuple[int, int] = (100, 300)

        # Mini-games configuration
        self.crystallize_initial_chance: float = 0.05
        self.crystallize_initial_multiplier_range: Tuple[float, float] = (0.8, 0.9)
        self.crystallize_chance_increment_range: Tuple[float, float] = (0.07, 0.16)
        self.crystallize_multiplier_increment_range: Tuple[float, float] = (0.1, 0.25)

        self.candy_pre_taken_weights: List[float] = [0.30, 0.5, 0.20]
        self.candy_win_multipliers: Dict[int, float] = {1: 1.1, 2: 1.8}

        self.coguard_initial_multiplier_range: Tuple[float, float] = (0.7, 0.8)
        self.coguard_multiplier_increment_range: Tuple[float, float] = (0.1, 0.2)

        self.staring_max_players: int = 6
        self.staring_lobby_duration: int = 60

        self.hole_game_duration: int = 30
        self.hole_items: Dict[int, str] = {
            0: "Ключ-карта ради О5 (0)",
            1: "MTF-E11-SR (1)",
            3: "Ключ-карта капітана МОГ (3)",
            5: "Бойова броня (5)",
            7: "Micro H.I.D. (7)",
            9: "Ключ-карта лейтенанта МОГ (9)",
            12: "FSP-9 (12)",
            14: "Світлошумова граната (14)",
            16: "Crossvec (16)",
            18: "Ключ-карта сержанта МОГ (9)",
            2: "Logicer (2)",
            4: "Пристрій доступу Повстанців Хаосу (4)",
            6: "AK (6)",
            8: ".44 Magnum (8)",
            10: "Адреналін (10)",
            11: "COM-18 (11)",
            13: "Осколково-фугасна граната (13)",
            15: "FR-MG-0 (15)",
            17: "Важка броня (17)",
            19: "Ключ-карта науковця (19)",
            21: "Аптечка (21)",
            23: "Ключ-карта наукового керівника (23)",
            25: "Ключ-карта інженера зі стримування (25)",
            27: "COM-15 (27)",
            30: "SCP-500 (30)",
            32: "Планшет (32)",
            34: "3-X Руйнівник частинок (34)",
            36: "Ключ-карта менеджера зони (36)",
            20: "Ключ-карта прибиральника (20)",
            22: "Шоколадний батончик (22)",
            24: "Порожня пляшка (24)",
            26: "Ліхтарик (26)",
            28: "Пошарпана книга (28)",
            29: "Стара фотографія (29)",
            31: "Пляшка води (31)",
            33: "Невідомий ключ (33)",
            35: "Черствий хліб (35)",
        }
        self.hole_group_bet_options: Dict[str, Dict] = {
            "Військові (1-18)": {
                "multiplier": 2,
                "numbers": set(range(1, 19))
            },
            "Цивільні (19-36)": {
                "multiplier": 2,
                "numbers": set(range(19, 37))
            },
            "Фонд SCP (MTF + Науковці)": {
                "multiplier": 2,
                "numbers": {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
            },
            "Повстанці Хаосу (Хаос + D-Клас)": {
                "multiplier": 2,
                "numbers": {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}
            },
            "Парні": {
                "multiplier": 2,
                "numbers": set(range(2, 37, 2))
            },
            "Непарні": {
                "multiplier": 2,
                "numbers": set(range(1, 37, 2))
            },
            "1-а дюжина (1-12)": {
                "multiplier": 3,
                "numbers": set(range(1, 13))
            },
            "2-а дюжина (13-24)": {
                "multiplier": 3,
                "numbers": set(range(13, 25))
            },
            "3-я дюжина (25-36)": {
                "multiplier": 3,
                "numbers": set(range(25, 37))
            },
            "1-й ряд": {
                "multiplier": 3,
                "numbers": {1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34}
            },
            "2-й ряд": {
                "multiplier": 3,
                "numbers": {2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35}
            },
            "3-й ряд": {
                "multiplier": 3,
                "numbers": {3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36}
            },
        }

        self.hole_bet_options: Dict[str, Dict] = {
            **self.hole_group_bet_options,
            **{name: {"multiplier": 36, "numbers": {num}} for num, name in self.hole_items.items()}
        }

        # Cooldowns configuration
        self.cooldown_type: BucketType = BucketType.user  # user for shared cooldown between guilds, guild for guild-based cooldown
        self.games_cooldown_rate: float = 3
        self.games_cooldown_time_minutes: float = 120
        self.work_cooldown_time_minutes: float = 240
        self.article_cooldown_time_minutes: float = 0.5

    def get_font(self, font_path: str, size: int) -> ImageFont.FreeTypeFont:
        if (font_path, size) not in self.fonts:
            self.fonts[(font_path, size)] = ImageFont.truetype(font_path, size=size)
        return self.fonts[(font_path, size)]

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

# Tortoise ORM configuration
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
