import logging
import os
import sys
from dataclasses import dataclass
from typing import List, Dict, Tuple

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

        self.discord_bot_token = self._get_env_variable("DISCORD_BOT_TOKEN")

        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.abspath(os.path.join(current_file_dir, "."))

        self.primary_font_path = os.path.join(self.project_root, "assets", "fonts", "Inter_18pt-Regular.ttf")
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
                "primary": "#2E2E2E",
                "secondary": "#4F4F4F",
                "embed": "#808080"
            },
            {
                "path": os.path.join(base_path, "keycard-7.png"),
                "primary": "#8BF3E8",
                "secondary": "#13C5B3",
                "embed": "#258F84"
            },
            {
                "path": os.path.join(base_path, "keycard-8.png"),
                "primary": "#2E2E2E",
                "secondary": "#717171",
                "embed": "#FFC74B"
            },
            {
                "path": os.path.join(base_path, "keycard-9.png"),
                "primary": "#484844",
                "secondary": "#858585",
                "embed": "#FFE18C"
            },
            {
                "path": os.path.join(base_path, "keycard-10.png"),
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
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s:     %(name)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
            ],
        )
        return logging.getLogger("scp-profiles")


config = Config()
logger = config.setup_logging()
