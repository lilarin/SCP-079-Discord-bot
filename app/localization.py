import json
import logging
from functools import reduce


class Localization:
    def __init__(self):
        self._translations = {}

    def load(self, locale_path: str):
        try:
            with open(locale_path, "r", encoding="utf-8") as f:
                self._translations = json.load(f)
        except FileNotFoundError:
            logging.error(f"Localization file not found at path: {locale_path}")
            exit(1)
        except json.JSONDecodeError:
            logging.error(f"Failed to read JSON from localisation file: {locale_path}")
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


t = Localization()
