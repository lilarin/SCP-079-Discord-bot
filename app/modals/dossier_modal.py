import asyncio

from disnake import ui, User, TextInputStyle, ModalInteraction

from app.core.models import User as UserModel
from app.services import achievement_handler_service
from app.utils.response_utils import response_utils


class DossierModal(ui.Modal):
    def __init__(self, user: User, db_user: UserModel) -> None:
        self.dossier = self._format_dossier(db_user)

        components = [
            ui.TextInput(
                label="Інформація",
                placeholder=self.dossier,
                custom_id="dossier",
                style=TextInputStyle.paragraph,
                min_length=20,
                max_length=1024,
                required=False,
            ),
        ]

        super().__init__(
            title=f"Досьє співробітника {user.display_name}",
            custom_id="dossierModal",
            components=components,
        )
        self.user = user
        self.db_user = db_user

    @staticmethod
    def _format_dossier(db_user: UserModel) -> str:
        return db_user.dossier[:97] + "..." if db_user.dossier else "..."

    async def callback(self, interaction: ModalInteraction) -> None:
        new_dossier = interaction.text_values.get("dossier")

        self.db_user.dossier = new_dossier
        await self.db_user.save()

        await response_utils.send_ephemeral_response(interaction, "Досьє оновлено!")

        asyncio.create_task(achievement_handler_service.handle_dossier_achievements(interaction.user))
