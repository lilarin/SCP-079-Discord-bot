from typing import Tuple

from disnake import Embed, File, ButtonStyle
from disnake.ui import Button, ActionRow

from app.config import config
from app.models import SCPObject


class ArticleUtils:
    @staticmethod
    def format_article_embed(article: SCPObject, image_file: File) -> Tuple[Embed, ActionRow]:
        embed = Embed(
            color=int(config.scp_class_config[article.object_class][0].lstrip('#'), 16)
        )
        name_confirm = Button(
            style=ButtonStyle.link,
            url=article.link,
            label="Переглянути статтю",
            emoji=config.scp_class_config[article.object_class][1],
        )

        embed.set_image(file=image_file)
        return embed, ActionRow(name_confirm)


article_utils = ArticleUtils()
