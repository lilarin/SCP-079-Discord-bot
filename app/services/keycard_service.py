import asyncio
from io import BytesIO
from typing import Tuple, Optional

from PIL import Image, ImageDraw
from cachetools import TTLCache
from disnake import File, User as DisnakeUser, Member

from app.config import config
from app.core.models import User
from app.core.schemas import CardConfig, UserProfileData
from app.utils.keycard_utils import keycard_utils

keycard_cache = TTLCache(maxsize=500, ttl=259200)


class KeyCardService:
    def __init__(self):
        self.image: Optional[Image.Image] = None
        self.draw: Optional[ImageDraw.Draw] = None

    async def get_user_profile_data(self, member: DisnakeUser | Member) -> UserProfileData:
        db_user, _ = await User.get_or_create(user_id=member.id)
        await db_user.fetch_related("equipped_card", "achievements")

        template = None
        if db_user.equipped_card:
            equipped_template_id = db_user.equipped_card.item_id
            if equipped_template_id in config.cards:
                template = config.cards[equipped_template_id]

        if not template:
            templates = list(config.cards.values())
            template = templates[-1]

        card_image = await self.get_or_generate_image(member, template)

        try:
            top_role = member.top_role if member.top_role != member.guild.default_role else None
        except AttributeError:
            top_role = None

        user_achievements_count = len(db_user.achievements)

        return UserProfileData(
            card_image=card_image,
            card_template=template,
            dossier=db_user.dossier,
            top_role=top_role,
            achievements_count=user_achievements_count
        )

    @staticmethod
    def _int_to_rgb(color_int: int) -> Tuple[int, int, int]:
        r = (color_int >> 16) & 0xFF
        g = (color_int >> 8) & 0xFF
        b = color_int & 0xFF
        return r, g, b

    def _add_text(
            self,
            text: str,
            position: Tuple[int, int],
            font_path: str,
            font_size: int,
            color: int
    ) -> None:
        font = config.get_font(font_path, font_size)
        fill_color = self._int_to_rgb(color)
        self.draw.text(position, text, font=font, fill=fill_color)

    def _add_spaced_text(
            self,
            text: str,
            position: Tuple[int, int],
            font_path: str,
            font_size: int,
            color: int,
            spacing: int
    ) -> None:
        font = config.get_font(font_path, font_size)
        fill_color = self._int_to_rgb(color)
        x, y = position
        for char in text:
            self.draw.text((x, y), char, font=font, fill=fill_color)
            char_width = self.draw.textlength(char, font=font)
            x += char_width + spacing

    def _add_circular_avatar(
            self,
            image_bytes: BytesIO,
            position: tuple[int, int],
            size: tuple[int, int]
    ) -> None:
        try:
            avatar = Image.open(image_bytes).convert("RGBA")
        except (FileNotFoundError, IOError):
            return

        avatar = avatar.resize(size, Image.Resampling.LANCZOS)

        supersample_multiplier = 4
        mask_size_large = (size[0] * supersample_multiplier, size[1] * supersample_multiplier)

        mask_large = Image.new("L", mask_size_large, 0)
        draw_large = ImageDraw.Draw(mask_large)

        draw_large.ellipse((0, 0) + mask_size_large, fill=255)

        mask_smooth = mask_large.resize(size, Image.Resampling.LANCZOS)

        self.image.paste(avatar, position, mask_smooth)

    def _add_overlay(
            self,
            image_bytes: BytesIO,
            position: Tuple[int, int],
            size: Tuple[int, int]
    ) -> None:
        try:
            decoration = Image.open(image_bytes).convert("RGBA")
        except (FileNotFoundError, IOError):
            return

        decoration = decoration.resize(size, Image.Resampling.LANCZOS)

        self.image.paste(decoration, position, decoration)

    def _process_template(
            self,
            template_image: Image.Image,
            user_name: str,
            user_code: str,
            avatar: BytesIO,
            primary_color: int,
            secondary_color: int,
            avatar_decoration: Optional[BytesIO] = None,
    ) -> File:
        self.image = template_image.copy().convert("RGBA")
        self.draw = ImageDraw.Draw(self.image)

        self._add_spaced_text(
            text=user_code,
            position=(630, 240),
            font_path=config.primary_font_path,
            font_size=45,
            color=secondary_color,
            spacing=30
        )
        self._add_circular_avatar(
            image_bytes=avatar,
            position=(1180, 510),
            size=(390, 390)
        )
        if avatar_decoration is not None:
            self._add_overlay(
                image_bytes=avatar_decoration,
                position=(1160, 492),
                size=(430, 430)
            )
        self._add_text(
            text=user_name,
            position=(53, 303),
            font_path=config.secondary_font_path,
            font_size=130,
            color=primary_color
        )

        image_buffer = BytesIO()
        self.image.save(image_buffer, format="PNG")
        image_buffer.seek(0)

        return File(fp=image_buffer, filename="keycard.png")

    async def get_or_generate_image(self, user: DisnakeUser | Member, template: CardConfig) -> File:
        cache_key = (
            user.id,
            template.name,
            user.display_name,
            user.joined_at.timestamp() if hasattr(user, "joined_at") and user.joined_at else None,
            getattr(user.avatar, "key", None),
            getattr(user.avatar_decoration, "key", None)
        )

        cached_file = keycard_cache.get(cache_key)
        if cached_file:
            cached_file.fp.seek(0)
            return cached_file

        user_id, user_name, user_code, avatar, avatar_decoration = await keycard_utils.collect_user_data(user)

        image_file = await asyncio.to_thread(
            self._process_template,
            template.image,
            user_name,
            user_code,
            avatar,
            template.primary_color,
            template.secondary_color,
            avatar_decoration,
        )

        keycard_cache[cache_key] = image_file

        image_file.fp.seek(0)
        return image_file


keycard_service = KeyCardService()
