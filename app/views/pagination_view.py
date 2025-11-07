from typing import Optional

from disnake import ui, ButtonStyle


class PaginationView(ui.View):
    def __init__(
            self,
            criteria: str,
            current_page: int = 1,
            disable_first: bool = False,
            disable_previous: bool = False,
            disable_next: bool = False,
            disable_last: bool = False,
            target_user_id: Optional[int] = None
    ):
        super().__init__(timeout=None)

        if all([disable_first, disable_previous, disable_next, disable_last]):
            return

        self.add_item(ui.Button(
            style=ButtonStyle.grey,
            label="⏪",
            custom_id=f"first_page_{criteria}_button",
            disabled=disable_first,
        ))
        self.add_item(ui.Button(
            style=ButtonStyle.grey,
            label="❮",
            custom_id=f"previous_page_{criteria}_button",
            disabled=disable_previous,
        ))
        self.add_item(ui.Button(
            style=ButtonStyle.grey,
            label=str(current_page),
            custom_id=f"current_page_{criteria}_button" if not target_user_id else str(target_user_id),
            disabled=True,
        ))
        self.add_item(ui.Button(
            style=ButtonStyle.grey,
            label="❯",
            custom_id=f"next_page_{criteria}_button",
            disabled=disable_next,
        ))
        self.add_item(ui.Button(
            style=ButtonStyle.grey,
            label="⏩",
            custom_id=f"last_page_{criteria}_button",
            disabled=disable_last,
        ))
