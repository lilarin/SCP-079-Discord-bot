import os
from typing import Dict, Tuple, Optional, List

from PIL import ImageFont
from disnake.ext.commands import BucketType

from app.core.schemas import CardConfig, WorkPrompts, AchievementConfig
from app.localization import t
from app.utils.configs_load_utils import configs_load_utils


class Variables:
    def __init__(self):
        # File System Paths variables
        self.project_root: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.assets_dir_path: str = os.path.join(self.project_root, "assets")
        self.locales_path: str = os.path.join(self.assets_dir_path, "configs", "locales.json")
        t.load(self.locales_path)

        self.cards_dir_path: str = os.path.join(self.assets_dir_path, "cards")
        self.shop_cards_path: str = os.path.join(self.assets_dir_path, "configs", "shop_cards.json")
        self.work_prompts_path: str = os.path.join(self.assets_dir_path, "configs", "work_prompts.json")
        self.achievements_config_path: str = os.path.join(self.assets_dir_path, "configs", "achievements.json")
        self.article_template_path: str = os.path.join(self.assets_dir_path, "articles", "article.png")
        self.primary_font_path: str = os.path.join(self.assets_dir_path, "fonts", "BauhausDemi.ttf")
        self.secondary_font_path: str = os.path.join(self.assets_dir_path, "fonts", "Inter_18pt-Bold.ttf")

        # Image, card and work prompts
        self.cards: Dict[str, CardConfig] = configs_load_utils.load_cards_from_json(self.shop_cards_path, self.cards_dir_path)
        self.work_prompts: Dict[str, WorkPrompts] = configs_load_utils.load_work_prompts_from_json(self.work_prompts_path)
        self.achievements: Dict[str, AchievementConfig] = configs_load_utils.load_achievements_from_json(self.achievements_config_path)

        # Image font cache
        self.fonts: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}

        # UI & Pagination
        self.leaderboard_options: Dict[str, str] = {v: k for k, v in t("leaderboard_options").items()}
        self.leaderboard_items_per_page: int = 10
        self.shop_items_per_page: int = 3
        self.inventory_items_per_page: int = 5
        self.achievements_per_page: int = 7

        # Economy
        self.legal_work_reward_range: Tuple[int, int] = (150, 350)
        self.non_legal_work_success_chance: float = 0.6
        self.non_legal_work_reward_range: Tuple[int, int] = (250, 500)
        self.non_legal_work_penalty_range: Tuple[int, int] = (200, 400)

        # Mini-games
        self.crystallize_initial_chance: float = 0.05
        self.crystallize_initial_multiplier_range: Tuple[float, float] = (0.9, 0.99)
        self.crystallize_chance_increment_range: Tuple[float, float] = (0.07, 0.16)
        self.crystallize_multiplier_increment_range: Tuple[float, float] = (0.11, 0.19)

        self.candy_pre_taken_weights: List[float] = [0.3, 0.5, 0.2]
        self.candy_win_multipliers: Dict[int, float] = {1: 1.25, 2: 2.99}

        self.coguard_initial_multiplier_range: Tuple[float, float] = (0.9, 1.1)
        self.coguard_multiplier_increment_range: Tuple[float, float] = (0.3, 0.65)

        self.schrodinger_win_multipliers: Dict[int, float] = {3: 1.35, 4: 2.4, 5: 3.5}
        self.schrodinger_container_names = ["A", "B", "C", "D", "E"]

        self.staring_max_players: int = 6
        self.staring_lobby_duration: int = 60

        self.hole_game_duration: int = 30
        self.hole_items: Dict[int, str] = {
            int(k): t(f"hole_items.{k}") for k, v in t("hole_items").items()
        }
        self.hole_group_bet_options: Dict[str, Dict] = {
            t(f"hole_group_bet_options.{key}.name"): {
                "multiplier": value["multiplier"],
                "numbers": set(value["numbers"]),
            }
            for key, value in t("hole_group_bet_options").items()
        }

        self.hole_bet_options: Dict[str, Dict] = {
            **self.hole_group_bet_options,
            **{name: {"multiplier": 36, "numbers": {num}} for num, name in self.hole_items.items()}
        }

        # Cooldowns
        self.cooldown_type: BucketType = BucketType.user
        # user for shared cooldown between guilds, guild for guild-based cooldown
        self.games_cooldown_rate: float = 3
        self.games_cooldown_time_minutes: float = 120
        self.work_cooldown_time_minutes: float = 240
        self.article_cooldown_time_minutes: float = 5

        # SCP Article Scraper
        self.wiki_url: str = "http://scp-ukrainian.wikidot.com"
        self.scp_classes: Dict[str, str] = {v: k for k, v in t("scp_classes").items()}
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
            f"{self.wiki_url}/scp-series-9",
        ]

    def get_font(self, font_path: str, size: int) -> ImageFont.FreeTypeFont:
        if (font_path, size) not in self.fonts:
            self.fonts[(font_path, size)] = ImageFont.truetype(font_path, size=size)
        return self.fonts[(font_path, size)]


variables = Variables()
