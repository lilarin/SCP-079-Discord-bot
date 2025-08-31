import json
import logging
from functools import reduce

from app.config import config


class Localization:
    def __init__(self, locales_path: str):
        self._translations = {}
        try:
            with open(locales_path, "r", encoding="utf-8") as f:
                self._translations = json.load(f)
        except FileNotFoundError:
            logging.error(f"Localization file not found at path: {locales_path}")
            exit(1)
        except json.JSONDecodeError:
            logging.error(f"Failed to read JSON from localisation file: {locales_path}")
            exit(1)
        except Exception as exception:
            logging.error(f"Unidentified error when downloading localization file: {exception}")
            exit(1)

    def __call__(self, key: str, **kwargs) -> str:
        try:
            value = reduce(lambda d, k: d[k], key.split("."), self._translations)
            if isinstance(value, str) and kwargs:
                return value.format(**kwargs)
            return value
        except (KeyError, TypeError):
            return key


t = Localization(locales_path=config.locales_path)
