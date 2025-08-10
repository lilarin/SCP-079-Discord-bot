import asyncio
import random
from typing import Dict

import disnake
from disnake import Embed

from app.config import config
from app.core.enums import Color
from app.core.models import User
from app.core.schemas import SCP173GameState
from app.services.economy_management_service import economy_management_service
from app.utils.response_utils import response_utils
from app.utils.ui_utils import ui_utils


class SCP173GameService:
    def __init__(self):
        self.games: Dict[int, SCP173GameState] = {}

    async def start_lobby(self, interaction: disnake.ApplicationCommandInteraction, bet: int, mode: str):
        host = interaction.author
        game_state = SCP173GameState(
            host=host,
            bet=bet,
            mode=mode,
            players={host},
            channel_id=interaction.channel_id
        )
        embed = await ui_utils.format_scp173_lobby_embed(game_state)
        components = await ui_utils.init_scp173_lobby_components(game_state)
        await response_utils.send_response(interaction, embed=embed, components=components)
        message = await interaction.original_message()
        game_state.message_id = message.id
        self.games[message.id] = game_state
        await asyncio.sleep(60)
        if message.id in self.games and not self.games[message.id].is_started:
            current_state = self.games[message.id]
            if len(current_state.players) < 2:
                await economy_management_service.update_user_balance(current_state.host.id, current_state.bet)
                message_to_edit = await interaction.original_message()
                await response_utils.edit_message(
                    message_to_edit,
                    content="Гра скасована: недостатньо гравців",
                    embed=None,
                    components=[]
                )
                del self.games[message.id]
            else:
                await self.run_game(interaction.channel, message.id)

    async def handle_join(self, interaction: disnake.MessageInteraction):
        message_id = interaction.message.id
        if message_id not in self.games or self.games[message_id].is_started:
            return await response_utils.send_ephemeral_response(interaction, "Ця гра вже закінчилася або почалася")
        game_state = self.games[message_id]
        user = interaction.author
        if user in game_state.players:
            return await response_utils.send_ephemeral_response(interaction, "Ви вже у грі")
        if len(game_state.players) >= config.staring_max_players:
            return await response_utils.send_ephemeral_response(interaction, "Лобі повне")
        db_user, _ = await User.get_or_create(user_id=user.id)
        if db_user.balance < game_state.bet:
            return await response_utils.send_ephemeral_response(interaction,
                                                                f"Недостатньо коштів. Потрібно {game_state.bet} 💠")
        await economy_management_service.update_user_balance(user.id, -game_state.bet)
        game_state.players.add(user)
        embed = await ui_utils.format_scp173_lobby_embed(game_state)
        components = await ui_utils.init_scp173_lobby_components(game_state)
        await response_utils.edit_response(interaction, embed=embed, components=components)
        if len(game_state.players) == config.staring_max_players:
            await self.run_game(interaction.channel, message_id)

    async def handle_start(self, interaction: disnake.MessageInteraction):
        message_id = interaction.message.id
        if message_id not in self.games or self.games[message_id].is_started:
            return await response_utils.send_ephemeral_response(interaction, "Ця гра вже закінчилася або почалася")
        game_state = self.games[message_id]
        if interaction.author.id != game_state.host.id:
            return await response_utils.send_ephemeral_response(interaction, "Тільки хост може розпочати гру")
        if len(game_state.players) < 2:
            return await response_utils.send_ephemeral_response(interaction, "Потрібно щонайменше 2 гравці для старту")
        await self.run_game(interaction.channel, message_id)

    async def run_game(self, channel: disnake.TextChannel, message_id: int):
        if message_id not in self.games or self.games[message_id].is_started:
            return

        game_state = self.games[message_id]
        game_state.is_started = True
        message = await channel.fetch_message(message_id)

        start_embed = await ui_utils.format_scp173_start_game_embed(game_state)
        info_components = await ui_utils.init_scp173_game_components(game_state)
        await response_utils.edit_message(message, embed=start_embed, components=info_components)

        await asyncio.sleep(3)

        survivors = list(game_state.players)
        total_players_at_start = len(survivors)
        round_number = 0

        while len(survivors) > 1:
            round_number += 1
            random.shuffle(survivors)
            current_round_survivors = []
            a_death_occurred = False

            denominator = max(config.staring_max_players - (round_number - 1), 1)
            death_chance = 1.0 / denominator

            for player in survivors:
                await asyncio.sleep(2)
                if random.random() < death_chance:
                    a_death_occurred = True
                    await response_utils.send_new_message(
                        channel,
                        message=f"**{player.mention}** кліпнув очима! Скульптура не пробачає помилок"
                    )
                else:
                    await response_utils.send_new_message(channel, message=f"**{player.mention}** не кліпнув очима")
                    current_round_survivors.append(player)

            survivors = current_round_survivors

            if game_state.mode == "normal" and a_death_occurred:
                pot = game_state.bet * total_players_at_start
                if not survivors:
                    embed = await ui_utils.format_scp173_no_survivors_embed()
                    await response_utils.send_new_message(channel, embed=embed)
                elif len(survivors) == 1:
                    winner = survivors[0]
                    await economy_management_service.update_user_balance(winner.id, pot)
                    embed = await ui_utils.format_scp173_single_winner_embed(winner, pot)
                    await response_utils.send_new_message(channel, embed=embed)
                else:
                    winnings_per_player = pot // len(survivors)
                    for winner in survivors:
                        await economy_management_service.update_user_balance(winner.id, winnings_per_player)
                    embed = await ui_utils.format_scp173_multiple_winners_embed(survivors, winnings_per_player)
                    await response_utils.send_new_message(channel, embed=embed)

                if message_id in self.games:
                    del self.games[message_id]
                return

            if len(survivors) <= 1:
                break

            description = f"**Раунд {round_number} завершено!**\n\n"
            if not a_death_occurred:
                description += "Дивно... ніхто не кліпав очима. "
            description += f"**{len(survivors)}** співробітників продовжують дивитися"

            await response_utils.send_new_message(
                channel, embed=Embed(description=description, color=Color.YELLOW.value)
            )
            await asyncio.sleep(4)

        if len(survivors) == 1:
            winner = survivors[0]
            pot = game_state.bet * total_players_at_start
            await economy_management_service.update_user_balance(winner.id, pot)
            embed = await ui_utils.format_scp173_single_winner_embed(winner, pot)
            await response_utils.send_new_message(channel, embed=embed)
        else:
            embed = await ui_utils.format_scp173_no_survivors_embed()
            await response_utils.send_new_message(channel, embed=embed)

        if message_id in self.games:
            del self.games[message_id]


scp173_game_service = SCP173GameService()
