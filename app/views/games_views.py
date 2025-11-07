from disnake import ui, ButtonStyle

from app.core.schemas import SCP173GameState
from app.core.variables import variables
from app.localization import t


class CrystallizationView(ui.View):
    def __init__(self, bet: int, multiplier: float, potential_win: int, loss_chance: float, is_first_turn: bool):
        super().__init__(timeout=None)

        self.add_item(ui.Button(
            style=ButtonStyle.secondary,
            label=t("ui.crystallize.bet_button", bet=bet),
            custom_id="display_bet",
            disabled=True,
            row=0
        ))
        self.add_item(ui.Button(
            style=ButtonStyle.secondary,
            label=t("ui.crystallize.multiplier_button", multiplier=f"{multiplier:.2f}"),
            custom_id="display_multiplier",
            disabled=True,
            row=0
        ))
        self.add_item(ui.Button(
            style=ButtonStyle.secondary,
            label=t("ui.crystallize.loss_chance_button", loss_chance=f"{loss_chance:.1f}"),
            custom_id="display_loss",
            disabled=True,
            row=0
        ))
        self.add_item(ui.Button(
            style=ButtonStyle.primary,
            label=t("ui.crystallize.continue_button"),
            custom_id="game_crystallize_continue",
            row=1
        ))
        self.add_item(ui.Button(
            style=ButtonStyle.green,
            label=t("ui.crystallize.cash_out_button", potential_win=potential_win),
            custom_id="game_crystallize_stop",
            disabled=is_first_turn,
            row=1
        ))


class CandyGameView(ui.View):
    def __init__(self, bet: int, pre_taken: int, player_taken: int, potential_win: int, multiplier: float,
                 is_first_turn: bool):
        super().__init__(timeout=None)

        swap_colors = bool(player_taken == 2)
        take_button_color, leave_button_color = (
            ButtonStyle.primary, ButtonStyle.green
        ) if not swap_colors else (
            ButtonStyle.green, ButtonStyle.primary
        )

        self.add_item(
            ui.Button(
                style=ButtonStyle.secondary,
                label=t("ui.candy_game.bet_button", bet=bet),
                custom_id="candy_display_bet",
                disabled=True, row=0
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.secondary,
                label=t("ui.candy_game.multiplier_button", multiplier=f"{multiplier:.1f}"),
                custom_id="candy_display_multiplier",
                disabled=True, row=0
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.secondary,
                label=t("ui.candy_game.taken_button", count=player_taken),
                custom_id=f"candy_state_{player_taken}_{pre_taken}",
                disabled=True, row=0
            )
        )
        self.add_item(
            ui.Button(
                style=take_button_color,
                label=t("ui.candy_game.take_button"),
                custom_id="game_candy_take", row=1
            )
        )
        self.add_item(
            ui.Button(
                style=leave_button_color,
                label=t("ui.candy_game.leave_button", potential_win=potential_win),
                custom_id="game_candy_leave",
                disabled=is_first_turn, row=1
            )
        )


class CoguardView(ui.View):
    def __init__(self, bet: int, multiplier: float, potential_win: int, current_number: int, win_streak: int,
                 is_first_turn: bool):
        super().__init__(timeout=None)

        self.add_item(
            ui.Button(
                style=ButtonStyle.secondary,
                label=t("ui.coguard_game.bet_button", bet=bet),
                custom_id="coguard_display_bet",
                disabled=True,
                row=0
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.secondary,
                label=t("ui.coguard_game.multiplier_button", multiplier=f"{multiplier:.2f}"),
                custom_id="coguard_display_multiplier",
                disabled=True, row=0
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.secondary,
                label=t("ui.coguard_game.number_button", number=current_number),
                custom_id="coguard_display_number",
                disabled=True,
                row=0
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.secondary,
                label=t("ui.coguard_game.streak_button", streak=win_streak),
                custom_id="coguard_display_streak",
                disabled=True,
                row=0
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.primary,
                label=t("ui.coguard_game.higher_button"), emoji="⬆️",
                custom_id="game_coguard_higher",
                row=1
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.primary,
                label=t("ui.coguard_game.lower_button"),
                emoji="⬇️",
                custom_id="game_coguard_lower",
                row=1
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.green,
                label=t("ui.coguard_game.cash_out_button", potential_win=potential_win),
                custom_id="game_coguard_cashout",
                disabled=is_first_turn, row=1
            )
        )


class StaringGameLobbyView(ui.View):
    def __init__(self, game_state: SCP173GameState):
        super().__init__(timeout=None)
        is_full = len(game_state.players) >= variables.staring_max_players
        mode_text = t("ui.staring_game.mode_lms") if game_state.mode == "last_man_standing" else t(
            "ui.staring_game.mode_normal")

        self.add_item(
            ui.Button(
                style=ButtonStyle.secondary,
                label=t("ui.staring_game.bet_button", bet=game_state.bet),
                custom_id="game_scp173_bet_display",
                disabled=True,
                row=0
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.secondary,
                label=f"{len(game_state.players)}/{variables.staring_max_players}",
                custom_id="game_scp173_count_display",
                disabled=True,
                row=0
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.secondary,
                label=t("ui.staring_game.mode_button", mode=mode_text),
                custom_id="game_scp173_mode_display",
                disabled=True, row=0
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.green,
                label=t("ui.staring_game.join_button"),
                custom_id="game_scp173_join",
                disabled=is_full, row=1
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.primary,
                label=t("ui.staring_game.start_button"),
                custom_id="game_scp173_start",
                row=1
            )
        )


class StaringGameInfoView(ui.View):
    def __init__(self, game_state: SCP173GameState):
        super().__init__(timeout=None)
        mode_text = t("ui.staring_game.mode_lms") if game_state.mode == "last_man_standing" else t(
            "ui.staring_game.mode_normal")

        self.add_item(
            ui.Button(
                style=ButtonStyle.secondary,
                label=t("ui.staring_game.bet_button", bet=game_state.bet),
                custom_id="game_scp173_bet_display",
                disabled=True
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.secondary,
                label=f"{len(game_state.players)}/{variables.staring_max_players}",
                custom_id="game_scp173_count_display",
                disabled=True
            )
        )
        self.add_item(
            ui.Button(
                style=ButtonStyle.secondary,
                label=t("ui.staring_game.mode_button", mode=mode_text),
                custom_id="game_scp173_mode_display",
                disabled=True
            )
        )
