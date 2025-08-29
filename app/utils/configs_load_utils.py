import json
import logging
import os
from typing import Dict

from PIL import Image

from app.core.schemas import (
    CardConfig,
    WorkPrompts,
    NonLegalPrompts,
    AchievementConfig
)


class ConfigsLoadUtils:
    @staticmethod
    def load_cards_from_json(shop_cards_path, cards_dir_path) -> Dict[str, CardConfig]:
        try:
            with open(shop_cards_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            loaded_cards: Dict[str, CardConfig] = {}
            for key, data in raw_data.items():
                full_image_path = os.path.join(cards_dir_path, data["image_file"])
                loaded_cards[key] = CardConfig(
                    name=data["name"],
                    description=data["description"],
                    price=data["price"],
                    quantity_range=tuple(data["quantity_range"]),
                    image=Image.open(full_image_path),
                    primary_color=int(data["colors"]["primary"].lstrip("#"), 16),
                    secondary_color=int(data["colors"]["secondary"].lstrip("#"), 16),
                    embed_color=int(data["colors"]["embed"].lstrip("#"), 16),
                    required_achievements=data.get("required_achievements")
                )
            return loaded_cards

        except FileNotFoundError:
            logging.error(f"Card config file not found at {shop_cards_path}")
            exit(1)
        except json.JSONDecodeError:
            logging.error(f"Could not decode JSON from {shop_cards_path}")
            exit(1)
        except KeyError as e:
            logging.error(f"Missing key in card data from {shop_cards_path}: {e}")
            exit(1)

    @staticmethod
    def load_work_prompts_from_json(work_prompts_path) -> Dict[str, WorkPrompts]:
        try:
            with open(work_prompts_path, "r", encoding="utf-8") as f:
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
            return loaded_prompts

        except FileNotFoundError:
            logging.error(f"Work prompts config file not found at {work_prompts_path}")
            exit(1)
        except json.JSONDecodeError:
            logging.error(f"Could not decode JSON from {work_prompts_path}")
            exit(1)
        except KeyError as e:
            logging.error(f"Missing key in work prompts data from {work_prompts_path}: {e}")
            exit(1)

    @staticmethod
    def load_achievements_from_json(achievements_config_path) -> Dict[str, AchievementConfig]:
        try:
            with open(achievements_config_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            loaded_achievements: Dict[str, AchievementConfig] = {}
            for key, data in raw_data.items():
                loaded_achievements[key] = AchievementConfig(
                    name=data["name"],
                    description=data["description"],
                    icon=data["icon"]
                )
            return loaded_achievements

        except FileNotFoundError:
            logging.error(f"Achievement config file not found at {achievements_config_path}")
            exit(1)
        except json.JSONDecodeError:
            logging.error(f"Could not decode JSON from {achievements_config_path}")
            exit(1)
        except KeyError as e:
            logging.error(f"Missing key in achievement data from {achievements_config_path}: {e}")
            exit(1)


configs_load_utils = ConfigsLoadUtils()
