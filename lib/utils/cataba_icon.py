import os
import textwrap
from typing import Optional

import requests
from jishaku.functools import executor_function
from PIL import Image, ImageDraw, ImageFilter, ImageFont


class BaseIcon:
    def __init__(self):
        self.primary_font = 'BurbankBigRegular-Black.ttf'
        self.secondary_font = 'BurbankSmall-Black.ttf'

    def draw_card_background(self, canvas: Image.Image, icon) -> None:
        try:
            background = Image.open(f'data/images/cataba_cards/card_background_{icon["rarity"]["value"]}.png')
        except FileNotFoundError:
            background = Image.open(f'data/images/cataba_cards/card_background_common.png')
        background = background.resize((512, 512), Image.ANTIALIAS)
        canvas.paste(background)

    def draw_card_faceplate(self, canvas: Image.Image, icon) -> None:
        try:
            faceplate = Image.open(f'data/images/cataba_cards/card_faceplate_{icon["rarity"]["value"]}.png')
        except FileNotFoundError:
            faceplate = Image.open(f'data/images/cataba_cards/card_faceplate_common.png')
        canvas.paste(faceplate, faceplate)

    def draw_text_background(
        self,
        canvas: Image.Image,
        text: str,
        x: int,
        y: int,
        font: ImageFont,
        fill: tuple
    ) -> None:
        blurred = Image.new('RGBA', canvas.size)
        draw = ImageDraw.Draw(blurred)
        draw.text(xy=(x, y), text=text, fill=fill, font=font)
        blurred = blurred.filter(ImageFilter.BoxBlur(10))

        # Paste soft text onto background
        canvas.paste(blurred, blurred)

    def draw_item_preview_image(self, canvas: Image.Image, icon):
        """"""
        if icon['images']['featured']:
            image = icon['images']['featured']
        elif icon['images']['icon']:
            image = icon['images']['icon']
        else:
            image = icon['images']['smallIcon']

        if not image and os.path.isfile('data/images/cataba_cards/placeholder.png'):
            image = Image.open('data/images/cataba_cards/placeholder.png')
        else:
            image = ImageUtils.download_image(image)
            if not image:
                return 0

        image = ImageUtils.ratio_resize(image, 512, 512)
        canvas.paste(image, image)

    def draw_display_name(self, canvas: Image.Image, c, icon):
        text_size = 32
        text = icon['name'].upper()
        if not text:
            return 0

        font = ImageUtils.open_font(font=self.primary_font, size=text_size)
        text_width, text_height = font.getsize(text)
        x = (512 - text_width) / 2
        while text_width > 512 - 4:
            text_size = text_size - 1
            font = ImageUtils.open_font(font=self.primary_font, size=text_size)
            text_width, text_height = font.getsize(text)
            x = (512 - text_width) / 2
        y = 425

        self.draw_text_background(canvas, text, x, y, font, (0, 0, 0, 215))
        c.text(
            (x, y),
            text,
            (255, 255, 255),
            font=font,
            align='center',
            stroke_width=1,
            stroke_fill=(0, 0, 0)
        )

    def draw_description(self, canvas: Image.Image, c, icon):
        text_size = 14
        text = icon['description']
        if not text:
            return 0
        text = text.upper()

        font = ImageUtils.open_font(font=self.secondary_font, size=text_size)

        if len(text) > 100:

            new_text = ""
            for des in textwrap.wrap(text, width=60):
                new_text += f'{des}\n'
            text = new_text  # Split the Description
            text_width, text_height = font.getsize(text)


            while text_width / 2 > 512 - 4:
                text_size = text_size - 1
                font = ImageUtils.open_font(font=self.secondary_font, size=text_size)
                text_width, text_height = font.getsize(text)

            if len(text.split('\n')) > 2:
                text_width = text_width / 2

            x = (512 - text_width) / 2
            y = 465 - text_height

            c.multiline_text(
                (x, y),
                text,
                fill='white',
                align='center',
                font=font,
            )
        else:
            text_width, text_height = font.getsize(text)
            x = (512 - text_width) / 2
            while text_width > 512 - 4:
                text_size = text_size - 1
                font = ImageUtils.open_font(font=self.secondary_font, size=text_size)
                text_width, text_height = font.getsize(text)
                x = (512 - text_width) / 2
            y = 460

            self.draw_text_background(canvas, text, x, y, font, (0, 0, 0, 215))
            c.text(
                (x, y),
                text=text,
                fill='white',
                font=font,
            )

    def draw_bottom_text(self, canvas: Image.Image, c, icon, side, text: str):
        if not icon['name'] or not icon['description']:
            return 0

        text_size = 17
        font = ImageUtils.open_font(font='BurbankBigRegular-Black.ttf', size=text_size)
        if side == 'left':
            text = f'C{text["chapter"]} S{text["season"]}'
            text_width, text_height = font.getsize(text)
            self.draw_text_background(
                canvas, text, 512 - 2 * 4 - text_width, 512 - 8 - text_height, font, (0, 0, 0))

            c.text(
                (512 - 2 * 4 - text_width, 512 - 8 - text_height),
                text,
                fill=(167, 184, 188),
                font=font,
                align='left'
            )
        else:
            text = '.'.join(text.split('.')[2:]).upper()
            text_width, text_height = font.getsize(text)
            self.draw_text_background(
                canvas, text, 8, 512 - 2 * 4 - text_height, font, (0, 0, 0, 215))

            c.text(
                (8, 512 - 2 * 4 - text_height),
                text,
                fill=(167, 184, 188),
                font=font,
                align='left'
            )

    def draw_user_flacing(self, canvas: Image.Image) -> Image.Image:
        cb = Image.open('data/images/cataba_cards/plus_sign.png')
        canvas.paste(cb, cb)

    @executor_function
    def generate_icon(self, data: dict) -> Image.Image:
        icon = data

        height = 512
        canvas = Image.new('RGB', (height, height))
        c = ImageDraw.Draw(canvas)
        self.draw_card_background(canvas, icon)
        self.draw_item_preview_image(canvas, icon)
        self.draw_card_faceplate(canvas, icon)
        if icon['name'] == "null":
            return 0
        self.draw_display_name(canvas, c, icon)
        self.draw_description(canvas, c, icon)
        if icon['introduction']:
            self.draw_bottom_text(canvas, c, icon, 'left', icon['introduction'])



        if icon['gameplayTags']:
            check_tags = list(
                filter(
                    lambda x: x.startswith('Cosmetics.Source.') or x.startswith('Athena.ItemAction.'),
                    icon['gameplayTags']
                )
            )

            if len(check_tags) > 0:
                self.draw_bottom_text(
                    canvas, c, icon, 'right', check_tags[0])


            userfacing = list(
                filter(
                    lambda x: x.startswith('Cosmetics.UserFacingFlags.'),
                    icon['gameplayTags']
                )
            )

            if len(userfacing) > 0:
                self.draw_user_flacing(canvas)

        return canvas


class ImageUtils:
    @staticmethod
    def download_image(url: str) -> Image.Image:
        """Download image from the URL and return the Pillow Image object."""

        res = requests.get(url, stream=True)
        if res.status_code == 200:
            return Image.open(res.raw).convert('RGBA')

    @staticmethod
    def ratio_resize(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """Resize and return the provided image while maintaining aspect ratio."""

        ratio = max(max_width / image.width, max_height / image.height)

        return image.resize(
            (int(image.width * ratio), int(image.height * ratio)), Image.ANTIALIAS
        )

    @staticmethod
    def open_font(
            size: int,
            font: str,
            directory: Optional[str] = 'data/fonts/',
    ) -> ImageFont.FreeTypeFont:
        """Open and return font located in provided directory."""

        try:
            return ImageFont.truetype(f'{directory}{font}', size)
        except OSError as e:
            print(f'{font} not found, defaulted font to BurbankBigRegular-Black.ttf')
            return ImageFont.truetype(f'{directory}BurbankBigRegular-Black.ttf', size)
        except Exception as e:
            print(f'Failed to load font, {e}')
