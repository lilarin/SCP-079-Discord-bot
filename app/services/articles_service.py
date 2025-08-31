import asyncio
import io
import textwrap

from PIL import Image, ImageDraw, ImageFont
from disnake import File

from app.config import config
from app.core.models import SCPObject


class ArticleService:
    def __init__(self):
        self.wiki_url = config.wiki_url
        self.template_path = config.article_template_path
        self.number_font_path = config.primary_font_path
        self.title_font_path = config.secondary_font_path

    @staticmethod
    def _draw_text_with_shadow(draw, pos, text, font, main_color):
        x, y = pos
        shadow_pos = (x + (2, 2)[0], y + (2, 2)[1])
        draw.text(shadow_pos, text, font=font, fill=(0, 0, 0, 150))
        draw.text(pos, text, font=font, fill=main_color)

    def _generate_image_sync(self, number: str, title: str) -> io.BytesIO:
        with Image.open(self.template_path).convert("RGBA") as base_image:
            img_width, img_height = base_image.size

            text_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(text_layer)

            number_font_size = int(img_height / 8)
            title_font_size = int(img_height / 10)
            number_font = ImageFont.truetype(self.number_font_path, number_font_size)
            title_font = ImageFont.truetype(self.title_font_path, title_font_size)

            avg_char_width = title_font_size * 0.6
            max_chars_per_line = int((img_width * 0.95) / avg_char_width)
            wrapped_title_lines = textwrap.wrap(title, width=max_chars_per_line, break_long_words=True)

            spacing_after_number = int(img_height / 20)
            title_line_bbox = draw.textbbox((0, 0), "A", font=title_font)
            title_line_height = title_line_bbox[3] - title_line_bbox[1]
            spacing_between_lines = int(title_line_height * 0.3)

            current_y = img_height / 2

            number_bbox = draw.textbbox((0, 0), number, font=number_font)
            number_width = number_bbox[2] - number_bbox[0]
            number_height = number_bbox[3] - number_bbox[1]
            number_x = (img_width - number_width) / 2
            self._draw_text_with_shadow(draw, (number_x, current_y), number, number_font, (50, 50, 50))
            current_y += number_height + spacing_after_number

            for line in wrapped_title_lines:
                line_bbox = draw.textbbox((0, 0), line, font=title_font)
                line_width = line_bbox[2] - line_bbox[0]
                line_x = (img_width - line_width) / 2
                self._draw_text_with_shadow(draw, (line_x, current_y), line, title_font, (50, 50, 50))
                current_y += title_line_height + spacing_between_lines

            out_image = Image.alpha_composite(base_image, text_layer)

            buffer = io.BytesIO()
            out_image.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer

    async def create_article_image(self, article: SCPObject) -> File:
        image_buffer = await asyncio.to_thread(
            self._generate_image_sync, article.number, article.title
        )

        return File(fp=image_buffer, filename=f"{article.number.lower()}_title.png")


article_service = ArticleService()
