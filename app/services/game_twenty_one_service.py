import asyncio
import io
import random
from pathlib import Path

from PIL import Image
from disnake import ApplicationCommandInteraction, Colour, File, MediaGalleryItem, MessageInteraction, SeparatorSpacing, ui

from app.core.enums import Color
from app.core.schemas import TwentyOneCard, TwentyOneGameState
from app.core.variables import variables
from app.localization import t
from app.services import economy_management_service
from app.views.games_views import TwentyOneView


class TwentyOneService:
    card_image_width = 96
    card_gap = 8
    result_colors = {
        "win": Color.GREEN,
        "tie": Color.YELLOW,
        "loss": Color.RED,
    }

    def __init__(self):
        self.games: dict[int, TwentyOneGameState] = {}

    @staticmethod
    def _create_deck() -> list[TwentyOneCard]:
        return [
            TwentyOneCard(
                rank=rank["id"],
                label=rank["label"],
                suit=suit,
                value=rank["value"],
            )
            for rank in variables.twenty_one["ranks"]
            for suit in variables.twenty_one["suits"]
        ]

    @staticmethod
    def _score(cards: list[TwentyOneCard]) -> int:
        score = sum(card.value for card in cards)
        aces = sum(card.rank == "A" for card in cards)
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    @staticmethod
    def _card_path(card: TwentyOneCard) -> Path:
        filename = variables.twenty_one["card_filename"].format(rank=card.rank, suit=card.suit)
        return Path(variables.playing_cards_dir_path) / filename

    @staticmethod
    def _backside_path() -> Path:
        return Path(variables.playing_cards_dir_path) / variables.twenty_one["backside_filename"]

    @staticmethod
    def _make_images_file(paths: list[Path], filename: str) -> File:
        width = TwentyOneService.card_image_width
        gap = TwentyOneService.card_gap
        images = []
        for path in paths:
            image = Image.open(path).convert("RGBA")
            height = round(image.height * width / image.width)
            images.append(image.resize((width, height), Image.Resampling.LANCZOS))

        strip = Image.new(
            "RGBA",
            (width * len(images) + gap * (len(images) - 1), max(image.height for image in images)),
            (0, 0, 0, 0),
        )
        offset = 0
        for image in images:
            strip.alpha_composite(image, (offset, 0))
            offset += width + gap

        stream = io.BytesIO()
        strip.save(stream, format="PNG")
        stream.seek(0)
        return File(stream, filename=filename)

    @staticmethod
    def _make_cards_file(cards: list[TwentyOneCard], filename: str) -> File:
        return TwentyOneService._make_images_file(
            [TwentyOneService._card_path(card) for card in cards], filename
        )

    @staticmethod
    def _build_components(
            state: TwentyOneGameState,
            reveal_dealer: bool = False,
            view: ui.View | None = None,
        result: str | None = None,
    ) -> tuple[list[ui.Container], list[File]]:
        cards = state.player_cards.copy()
        dealer_cards = state.dealer_cards.copy()
        dealer_upcard = dealer_cards[variables.twenty_one["dealer_upcard_index"]]
        player_score = TwentyOneService._score(cards)
        dealer_score = TwentyOneService._score(dealer_cards) if reveal_dealer else dealer_upcard.value
        files = [
            TwentyOneService._make_cards_file(cards, "twenty_one_player.png"),
            TwentyOneService._make_images_file(
                ([TwentyOneService._backside_path()] + [TwentyOneService._card_path(
                    dealer_cards[variables.twenty_one["dealer_upcard_index"]]
                )])
                if not reveal_dealer else [TwentyOneService._card_path(card) for card in dealer_cards],
                "twenty_one_dealer.png",
            ),
        ]
        if result:
            components = [
                ui.TextDisplay(f"### {t(f'ui.twenty_one.result_{result}_title')}"),
            ]
        else:
            components = [ui.TextDisplay(t("ui.twenty_one.board", bet=state.bet))]
        components.extend([
            ui.TextDisplay(t("ui.twenty_one.player_cards", score=player_score)),
            ui.MediaGallery(MediaGalleryItem(
                "attachment://twenty_one_player.png",
                description=", ".join(card.label for card in cards),
            )),
            ui.TextDisplay(t("ui.twenty_one.dealer_cards", score=dealer_score)),
            ui.MediaGallery(MediaGalleryItem(
                "attachment://twenty_one_dealer.png",
                description=dealer_upcard.label if not reveal_dealer else ", ".join(
                    card.label for card in dealer_cards
                ),
            )),
        ])
        if result:
            components.extend([
                ui.Separator(divider=False, spacing=SeparatorSpacing.large),
                ui.TextDisplay(t(
                    "ui.twenty_one.result_payout",
                    label=t(f"ui.twenty_one.result_{result}_payout_label"),
                    amount=state.bet if result == "loss" else int(
                        state.bet * variables.twenty_one[f"{result}_payout_multiplier"]
                    ),
                )),
            ])
        if view is not None:
            components.append(ui.ActionRow(*view.children))
        accent_colour = Colour(
            TwentyOneService.result_colors.get(result, Color.BLUE).value
        )
        return [ui.Container(*components, accent_colour=accent_colour)], files

    async def _render(self, interaction, state: TwentyOneGameState, reveal_dealer: bool = False, view=None):
        components, files = self._build_components(state, reveal_dealer, view)
        await interaction.edit_original_response(components=components, files=files)

    async def start_game(self, interaction: ApplicationCommandInteraction, bet: int):
        deck = self._create_deck()
        random.shuffle(deck)
        state = TwentyOneGameState(
            bet=bet,
            deck=deck,
            player_cards=[deck.pop(), deck.pop()],
            dealer_cards=[deck.pop(), deck.pop()],
        )
        components, files = self._build_components(
            state, view=TwentyOneView()
        )
        message = await interaction.edit_original_response(components=components, files=files)
        self.games[message.id] = state
        if self._score(state.player_cards) > 21:
            await self._finish(interaction, message.id)

    async def hit(self, interaction: MessageInteraction):
        state = self.games[interaction.message.id]
        if state.dealer_turn:
            await self._render(interaction, state, reveal_dealer=True)
            return
        state.player_cards.append(state.deck.pop())
        score = self._score(state.player_cards)
        if score > 21:
            await self._finish(interaction, interaction.message.id)
        else:
            await self._render(interaction, state, view=TwentyOneView())

    async def stand(self, interaction: MessageInteraction):
        state = self.games[interaction.message.id]
        if state.dealer_turn:
            await self._render(interaction, state, reveal_dealer=True)
            return
        await self._dealer_turn(interaction, interaction.message.id)

    async def _dealer_turn(self, interaction: MessageInteraction, message_id: int):
        state = self.games[message_id]
        state.dealer_turn = True
        await self._render(interaction, state, reveal_dealer=True)
        await asyncio.sleep(1)

        while self._score(state.dealer_cards) < variables.twenty_one["dealer_draw_threshold"]:
            state.dealer_cards.append(state.deck.pop())
            await self._render(interaction, state, reveal_dealer=True)
            await asyncio.sleep(1)

        await self._finish(interaction, message_id)

    async def _finish(self, interaction, message_id: int):
        state = self.games.pop(message_id)

        player_score = self._score(state.player_cards)
        dealer_score = self._score(state.dealer_cards)
        result = "loss" if player_score > 21 or (dealer_score <= 21 and dealer_score > player_score) else (
            "tie" if dealer_score == player_score else "win"
        )
        multiplier = variables.twenty_one[f"{result}_payout_multiplier"]
        payout = int(state.bet * multiplier)
        if payout:
            await economy_management_service.update_user_balance(
                interaction.user, payout, t(f"economy.reasons.game_{result}_twenty_one")
            )
        components, files = self._build_components(state, reveal_dealer=True, result=result)
        await interaction.edit_original_response(components=components, files=files)


twenty_one_service = TwentyOneService()
