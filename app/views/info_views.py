from disnake import ui, ButtonStyle

from app.core.models import SCPObject
from app.core.variables import variables
from app.localization import t


class ArticleView(ui.View):
    def __init__(self, article: SCPObject):
        super().__init__(timeout=None)
        self.add_item(ui.Button(
            style=ButtonStyle.link,
            url=article.link,
            label=t("ui.article.view_button"),
            emoji=variables.scp_class_config[article.object_class][1],
        ))
