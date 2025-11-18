import asyncio
import base64
import hashlib
import random

from disnake import ui, ApplicationCommandInteraction, MessageInteraction

from app.config import config
from app.core.variables import variables
from app.embeds import games_embeds
from app.localization import t
from app.services import achievement_handler_service, economy_management_service
from app.utils.response_utils import response_utils
from app.views.games_views import CandyGameView


class CandyGameService:
    @staticmethod
    def _get_session_key(message_id: int) -> bytes:
        data_to_hash = f"{message_id}_{config.discord_bot_token}".encode("utf-8")
        return hashlib.sha256(data_to_hash).digest()

    @staticmethod
    def _obfuscate_state(player_taken: int, pre_taken: int, message_id: int) -> str:
        state_string = f"{player_taken}:{pre_taken}".encode("utf-8")
        key = CandyGameService._get_session_key(message_id)

        encrypted_bytes = bytearray()
        for i, byte_to_encrypt in enumerate(state_string):
            key_byte = key[i % len(key)]
            encrypted_bytes.append(byte_to_encrypt ^ key_byte)

        return base64.urlsafe_b64encode(bytes(encrypted_bytes)).decode()

    @staticmethod
    def _deobfuscate_state(obfuscated_string: str, message_id: int) -> tuple[int, int]:
        key = CandyGameService._get_session_key(message_id)
        decoded_bytes = base64.urlsafe_b64decode(obfuscated_string.encode())

        decrypted_bytes = bytearray()
        for i, byte_to_decrypt in enumerate(decoded_bytes):
            key_byte = key[i % len(key)]
            decrypted_bytes.append(byte_to_decrypt ^ key_byte)

        state_string = decrypted_bytes.decode("utf-8")
        player_taken_str, pre_taken_str = state_string.split(":")
        return int(player_taken_str), int(pre_taken_str)

    @staticmethod
    def _parse_state_from_components(components: list[ui.ActionRow], message_id: int) -> tuple[int, int, int]:
        state_id = components[0].children[2].custom_id
        obfuscated_part = state_id.split("_")[2]

        player_taken, pre_taken = CandyGameService._deobfuscate_state(obfuscated_part, message_id)

        bet_label = components[0].children[0].label
        bet = int(bet_label.split(":")[1].strip().split(" ")[0])

        return bet, pre_taken, player_taken

    @staticmethod
    async def start_game(interaction: ApplicationCommandInteraction, bet: int):
        pre_taken = random.choices([0, 1, 2], weights=variables.candy_pre_taken_weights, k=1)[0]
        player_taken = 0

        embed = await games_embeds.format_candy_game_embed()
        await response_utils.send_response(interaction, embed=embed)
        message = await interaction.original_response()

        obfuscated_state = CandyGameService._obfuscate_state(player_taken, pre_taken, message.id)

        final_view = CandyGameView(
            bet=bet,
            obfuscated_state=obfuscated_state,
            player_taken=player_taken,
            potential_win=bet,
            multiplier=1.0,
            is_first_turn=True
        )
        await response_utils.edit_message(message, embed=embed, view=final_view)

    async def take_candy(self, interaction: MessageInteraction):
        message_id = interaction.message.id
        bet, pre_taken, player_taken = self._parse_state_from_components(interaction.message.components, message_id)
        player_taken += 1

        if pre_taken + player_taken >= 3:
            loss_embed = await games_embeds.format_candy_loss_embed(bet=bet)
            await response_utils.edit_response(interaction, embed=loss_embed, view=None)
            asyncio.create_task(
                achievement_handler_service.handle_candy_achievements(
                    interaction.user, player_taken, is_loss=True
                )
            )
            return

        multiplier = variables.candy_win_multipliers.get(player_taken, 1.0)
        potential_win = int(bet * multiplier)

        obfuscated_state = self._obfuscate_state(player_taken, pre_taken, message_id)

        embed = await games_embeds.format_candy_game_embed()
        view = CandyGameView(
            bet=bet,
            obfuscated_state=obfuscated_state,
            player_taken=player_taken,
            potential_win=potential_win,
            multiplier=multiplier,
            is_first_turn=False
        )
        await response_utils.edit_response(interaction, embed=embed, view=view)

    async def leave_game(self, interaction: MessageInteraction):
        message_id = interaction.message.id
        bet, _, player_taken = self._parse_state_from_components(interaction.message.components, message_id)
        multiplier = variables.candy_win_multipliers.get(player_taken, 1.0)
        winnings = int(bet * multiplier)

        await economy_management_service.update_user_balance(
            interaction.user, winnings, t("economy.reasons.game_win_candy")
        )
        win_embed = await games_embeds.format_candy_win_embed(winnings=winnings)
        await response_utils.edit_response(interaction, embed=win_embed, view=None)

        asyncio.create_task(
            achievement_handler_service.handle_candy_achievements(interaction.user, player_taken, is_loss=False)
        )


candy_game_service = CandyGameService()
