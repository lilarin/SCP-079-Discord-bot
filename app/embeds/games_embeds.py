from typing import List, Tuple, Optional

from disnake import Embed, User

from app.core.enums import Color
from app.core.schemas import SCP173GameState, HoleGameState
from app.core.variables import variables
from app.localization import t


async def format_crystallize_embed(bet: int) -> Embed:
    embed = Embed(
        title=t("ui.crystallize.title"),
        description=t("ui.crystallize.description"),
        color=Color.LIGHT_PINK.value
    )
    embed.set_thumbnail(url="https://imgur.com/DOAsTfy.png")
    return embed


async def format_crystallize_win_embed(bet: int, winnings: int, multiplier: float) -> Embed:
    embed = Embed(
        title=t("ui.crystallize.win_title"),
        description=t(
            "ui.crystallize.win_description", bet=bet, multiplier=f"{multiplier:.2f}", winnings=winnings
        ),
        color=Color.GREEN.value
    )
    embed.set_thumbnail(url="https://imgur.com/DOAsTfy.png")
    return embed


async def format_crystallize_loss_embed(bet: int) -> Embed:
    embed = Embed(
        title=t("ui.crystallize.loss_title"),
        description=t("ui.crystallize.loss_description", bet=bet),
        color=Color.RED.value
    )
    embed.set_thumbnail(url="https://imgur.com/DOAsTfy.png")
    return embed


async def format_coin_flip_win_embed(bet: int) -> Embed:
    embed = Embed(
        title=t("ui.coin_flip.win_title"),
        description=t("ui.coin_flip.win_description", bet=bet),
        color=Color.GREEN.value
    )
    embed.set_thumbnail(url="https://imgur.com/n4znTOU.png")
    return embed


async def format_coin_flip_loss_embed(bet: int) -> Embed:
    embed = Embed(
        title=t("ui.coin_flip.loss_title"),
        description=t("ui.coin_flip.loss_description", bet=bet),
        color=Color.RED.value
    )
    embed.set_thumbnail(url="https://imgur.com/n4znTOU.png")
    return embed


async def format_candy_game_embed() -> Embed:
    embed = Embed(
        title=t("ui.candy_game.title"),
        description=t("ui.candy_game.description"),
        color=Color.ORANGE.value
    )
    embed.set_thumbnail(url="https://i.imgur.com/6oHifKt.png")
    return embed


async def format_candy_win_embed(winnings: int) -> Embed:
    embed = Embed(
        title=t("ui.candy_game.win_title"),
        description=t("ui.candy_game.win_description", winnings=winnings),
        color=Color.GREEN.value
    )
    embed.set_thumbnail(url="https://i.imgur.com/6oHifKt.png")
    return embed


async def format_candy_loss_embed(bet: int) -> Embed:
    embed = Embed(
        title=t("ui.candy_game.loss_title"),
        description=t("ui.candy_game.loss_description", bet=bet),
        color=Color.RED.value
    )
    embed.set_thumbnail(url="https://i.imgur.com/6oHifKt.png")
    return embed


async def format_coguard_embed(current_number: int) -> Embed:
    embed = Embed(
        title=t("ui.coguard_game.title"),
        description=t("ui.coguard_game.description", current_number=current_number),
        color=Color.BLUE.value
    )
    embed.set_thumbnail(url="https://imgur.com/pAW9s4O.png")
    return embed


async def format_coguard_win_embed(bet: int, winnings: int, multiplier: float, win_streak: int) -> Embed:
    embed = Embed(
        title=t("ui.coguard_game.win_title"),
        description=t(
            "ui.coguard_game.win_description",
            bet=bet,
            win_streak=win_streak,
            multiplier=f"{multiplier:.2f}",
            winnings=winnings
        ),
        color=Color.GREEN.value
    )
    embed.set_thumbnail(url="https://imgur.com/pAW9s4O.png")
    return embed


async def format_coguard_loss_embed(bet: int, win_streak: int) -> Embed:
    embed = Embed(
        title=t("ui.coguard_game.loss_title"),
        description=t("ui.coguard_game.loss_description", win_streak=win_streak, bet=bet),
        color=Color.RED.value
    )
    embed.set_thumbnail(url="https://imgur.com/pAW9s4O.png")
    return embed


async def format_scp173_lobby_embed(game_state: SCP173GameState) -> Embed:
    embed = Embed(
        title=t("ui.staring_game.title"),
        description=t("ui.staring_game.lobby_description"),
        color=Color.WHITE.value
    )
    embed.set_thumbnail(url="https://imgur.com/PJPoIes.png")

    player_list = "\n".join(
        [f"{i + 1}. {player.mention}" for i, player in enumerate(list(game_state.players))]
    )
    embed.add_field(
        name=t("ui.staring_game.players_field"),
        value=player_list if player_list else t("ui.staring_game.no_players"),
        inline=False
    )
    embed.set_footer(text=t("ui.staring_game.lobby_footer", duration=variables.staring_lobby_duration))
    return embed


async def format_scp173_start_game_embed(
        game_state: SCP173GameState, round_logs: Optional[List[dict]] = None
) -> Embed:
    player_list = "\n".join(
        [f"{i + 1}. {player.mention}" for i, player in enumerate(list(game_state.players))]
    )
    embed = Embed(
        title=t("ui.staring_game.game_start_title"),
        description=t("ui.staring_game.game_start_description"),
        color=Color.BLACK.value
    )
    embed.set_thumbnail(url="https://imgur.com/fBmiMNB.png")
    embed.add_field(name=t("ui.staring_game.players_field"), value=player_list, inline=False)

    if round_logs:
        for round_field in round_logs:
            field_value = round_field.get("value") or "..."
            embed.add_field(
                name=round_field.get("name"),
                value=field_value,
                inline=round_field.get("inline", False),
            )
    return embed


async def format_scp173_single_winner_embed(winner: User, pot: int) -> Embed:
    embed = Embed(
        title=t("ui.staring_game.single_winner_title"),
        description=t("ui.staring_game.single_winner_description", winner_mention=winner.mention, pot=pot),
        color=Color.GREEN.value
    )
    embed.set_thumbnail(url="https://imgur.com/PJPoIes.png")
    return embed


async def format_scp173_multiple_winners_embed(winners: List[User], winnings_per_player: int) -> Embed:
    winner_mentions = ", ".join([w.mention for w in winners])
    embed = Embed(
        title=t("ui.staring_game.multi_winner_title"),
        description=t(
            "ui.staring_game.multi_winner_description",
            winner_mentions=winner_mentions,
            winnings=winnings_per_player
        ),
        color=Color.GREEN.value
    )
    embed.set_thumbnail(url="https://imgur.com/PJPoIes.png")
    return embed


async def format_scp173_no_survivors_embed() -> Embed:
    embed = Embed(
        title=t("ui.staring_game.no_survivors_title"),
        description=t("ui.staring_game.no_survivors_description"),
        color=Color.RED.value
    )
    embed.set_thumbnail(url="https://imgur.com/fBmiMNB.png")
    return embed


async def format_hole_lobby_embed(game_state: HoleGameState) -> Embed:
    embed = Embed(
        title=t("ui.hole_game.title"),
        color=Color.WHITE.value
    )
    embed.set_thumbnail(url="https://imgur.com/vHlPfOR.png")

    embed.description = t("ui.hole_game.current_bets")
    for i, bet in enumerate(game_state.bets):
        embed.description += f"{i + 1}. {bet.player.mention} **{bet.amount}** 💠 на `{bet.choice}`\n"

    embed.set_footer(text=t("ui.hole_game.lobby_footer", duration=variables.hole_game_duration))
    return embed


async def format_hole_results_embed(
        winning_item: str, winners: List[Tuple[User, int]]
) -> Embed:
    embed = Embed(
        title=t("ui.hole_game.result_title"),
        description=f"``{winning_item}``\n",
        color=Color.GREEN.value if winners else Color.RED.value
    )
    embed.set_thumbnail(url="https://imgur.com/vHlPfOR.png")

    if winners:
        winner_lines = []
        for i, (player, payout) in enumerate(winners):
            winner_lines.append(f"{i + 1}. {player.mention} виграв **{payout}** 💠")
        embed.add_field(name=t("ui.hole_game.winners_field"), value="\n".join(winner_lines), inline=False)
    else:
        embed.description += t("ui.hole_game.no_winners")

    return embed


async def format_schrodinger_initial_choice_embed(num_containers: int) -> Embed:
    embed = Embed(
        title=t("ui.schrodinger_game.title"),
        description=t(
            "ui.schrodinger_game.initial_description",
             count=num_containers
        ),
        color=Color.BLACK.value
    )
    embed.set_thumbnail(url="https://i.imgur.com/rUsdAZG.png")
    return embed


async def format_schrodinger_win_embed(winnings: int, winning_container_index: int, player_stayed: bool) -> Embed:
    container_name = variables.schrodinger_container_names[winning_container_index]

    embed = Embed(
        title=t("ui.schrodinger_game.win_title"),
        description=t(
            "ui.schrodinger_game.win_description",
            container=container_name,
            winnings=winnings
        ),
        color=Color.GREEN.value
    )
    embed.set_thumbnail(url="https://i.imgur.com/rUsdAZG.png")
    return embed


async def format_schrodinger_loss_embed(bet: int, winning_container_index: int) -> Embed:
    container_name = variables.schrodinger_container_names[winning_container_index]
    embed = Embed(
        title=t("ui.schrodinger_game.loss_title"),
        description=t(
            "ui.schrodinger_game.loss_description",
            container=container_name,
            bet=bet
        ),
        color=Color.RED.value
    )
    embed.set_thumbnail(url="https://i.imgur.com/rUsdAZG.png")
    return embed
