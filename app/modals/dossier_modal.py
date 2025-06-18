import disnake

from app.models import User
from app.utils.response_utils import response_utils


class DossierModal(disnake.ui.Modal):
    def __init__(self, user: disnake.User, db_user: User) -> None:
        self.dossier = self._format_dossier(db_user)

        components = [
            disnake.ui.TextInput(
                label="Інформація",
                placeholder=self.dossier,
                custom_id="dossier",
                style=disnake.TextInputStyle.paragraph,
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
    def _format_dossier(db_user: User) -> str:
        return db_user.dossier[:97] + "..." if db_user else "..."

    async def callback(self, interaction: disnake.ModalInteraction) -> None:
        new_dossier = interaction.text_values.get("dossier")

        self.db_user.dossier = new_dossier
        await self.db_user.save()

        await response_utils.send_ephemeral_response(interaction, "Досьє оновлено!")
