import json
import logging
from math import ceil
from sys import exit
from time import sleep

import coloredlogs
from PIL import Image, ImageDraw

from util import ImageUtil, Utility

log = logging.getLogger(__name__)
coloredlogs.install(
    level="INFO", fmt="[%(asctime)s] %(message)s", datefmt="%I:%M:%S")


class Athena:
    """Fortnite Item Shop Generator."""

    def main(self):

        initialized = Athena.LoadConfiguration(self)

        if initialized is True:
            if self.delay > 0:
                log.info(f"Delaying process start for {self.delay}s...")
                sleep(self.delay)

            itemShop = Utility.GET(
                self,
                "https://fortnite-api.com/v2/shop/br/combined",
                {"x-api-key": self.apiKey},
                {"language": self.language},
            )

            if itemShop is not None:
                itemShop = json.loads(itemShop)["data"]

                # Strip time from the timestamp, we only need the date
                date = Utility.ISOtoHuman(
                    self, itemShop["date"].split("T")[0], self.language
                )
                log.info(f"Retrieved Item Shop for {date}")

                Athena.GenerateImage(self, date, itemShop)


    def LoadConfiguration(self):
        """
        Set the configuration values specified in configuration.json

        Return True if configuration sucessfully loaded.
        """

        configuration = json.loads(
            Utility.ReadFile(self, "configuration", "json"))

        try:
            self.delay = configuration["delayStart"]
            self.apiKey = configuration["fortniteAPI"]["apiKey"]
            self.language = configuration["language"]

            log.info("Loaded configuration")

            return True
        except Exception as e:
            log.critical(f"Failed to load configuration, {e}")

    def GenerateImage(self, date: str, itemShop: dict):
        """
        Generate the Item Shop image using the provided Item Shop.

        Return True if image sucessfully saved.
        """

        try:
            if itemShop["featured"] is not None:
                featured = itemShop["featured"]["entries"]

            else:
                featured = []

            if itemShop["daily"] is not None:
                daily = itemShop["daily"]["entries"]

            else:
                daily = []


            if (len(featured) >= 0):
                rowsDaily = 3
                rowsFeatured = 6
                width = ((340 * 9) + 10)
                height = max(ceil(len(featured) / 6), ceil(len(daily) / 3))
                dailyStartX = 2075
                cardStartY = 450

            if (len(featured) <= 18):
                rowsDaily = 3
                rowsFeatured = 3
                width = ((340 * 6) + 10)
                height = max(ceil(len(featured) / 3), ceil(len(daily) / 3))
                dailyStartX = 1055
                cardStartY = 350

            if (len(featured) >= 24) and (len(daily) >= 18):
                rowsDaily = 6
                rowsFeatured = 6
                width = ((340 * 12) - 25)
                height = max(ceil(len(featured) / 6), ceil(len(daily) / 6))
                dailyStartX = 2075
                cardStartY = 450

            if (len(featured) >= 42) :
                rowsDaily = 4
                rowsFeatured = 9
                width = ((340 * 13) + 5)
                height = max(ceil(len(featured) / 9), ceil(len(daily) / 4))
                dailyStartX = 3095
                cardStartY = 650

        except Exception as e:
            log.critical(f"Failed to parse Item Shop Featured and Daily items, {e}")
            return False

        # Determine the max amount of rows required for the current
        # This allows us to determine the image height.

        shopImage = Image.new("RGBA", (width, (530 * height) + cardStartY))

        try:
            background = ImageUtil.Open(self, f"background.png")#
            background = ImageUtil.RatioResize(
                self, background, shopImage.width, shopImage.height
            )
            shopImage.paste(
                background, ImageUtil.CenterX(
                    self, background.width, shopImage.width)
            )
        except FileNotFoundError:
            log.warning(
                "Failed to open background.png, defaulting to dark gray")
            shopImage.paste(
                (34, 37, 40), [0, 0, shopImage.size[0], shopImage.size[1]])


        #logo = ImageUtil.Open(self, "logo.png")
        #logo = ImageUtil.RatioResize(self, logo, 20, 250)
        #shopImage.paste(
        #    logo, ImageUtil.CenterX(self, logo.width, shopImage.width, 5), logo
        #)

        #canvas = ImageDraw.Draw(shopImage)
        #font = ImageUtil.Font(self, 80)

        #textWidth, _ = font.getsize("Магазин предметов Fortnite")
        #canvas.text(ImageUtil.CenterX(self, textWidth, shopImage.width, 30), "Магазин предметов Fortnite", (255, 255, 255), font=font)
        #textWidth, _ = font.getsize(date.upper())
        #canvas.text(ImageUtil.CenterX(self, textWidth, shopImage.width, 240), date.upper(), (255, 255, 255), font=font)

        #canvas.text((20, 240), "Рекомендуемые предметы", (255, 255, 255), font=font, anchor=None, spacing=4, align="left")
        #textWidth, _ = font.getsize("Ежедневный магазин")
        #canvas.text((shopImage.width - (textWidth + 20), 240), "Ежедневный магазин", (255, 255, 255), font=font, anchor=None, spacing=4, align="right")

        # Track grid position
        i = 0

        for item in featured:
            card = Athena.GenerateCard(self, item)

            if card is not None:
                shopImage.paste(
                    card,
                    (
                        (20 + ((i % rowsFeatured) * (310 + 20))),
                        (cardStartY + ((i // rowsFeatured) * (510 + 20))),
                    ),
                    card,
                )

                i += 1

        # Reset grid position
        i = 0

        for item in daily:
            card = Athena.GenerateCard(self, item)

            if card is not None:
                shopImage.paste(
                    card,
                    (
                        (dailyStartX + ((i % rowsDaily) * (310 + 20))),
                        (cardStartY + ((i // rowsDaily) * (510 + 20))),
                    ),
                    card,
                )

                i += 1

        try:
            shopImage.save("athena/itemshop.png")
            shopImageJPG = Image.open('athena/itemshop.png')
            shopImageJPG = shopImageJPG.convert("RGB")
            shopImageJPG.save("athena/itemshop.jpg", optimize=True, quality=80)
            log.info("Generated Item Shop image [png & jpg]")

            return True
        except Exception as e:
            log.critical(f"Failed to save Item Shop image, {e}")

    def GenerateCard(self, item: dict):
        """Return the card image for the provided Fortnite Item Shop item."""

        try:
            name = item["items"][0]["name"].lower()
            rarity = item["items"][0]["rarity"]["value"].lower()
            category = item["items"][0]["type"]["value"].lower()
            price = item["finalPrice"]


            if (item["items"][0]["images"]["featured"]):
                icon = item["items"][0]["images"]["featured"]
            else:
                icon = item["items"][0]["images"]["icon"]

            if(item["bundle"]):
                icon = item["bundle"]["image"]
                name = item["bundle"]["name"].lower()
                category = "Bundle".lower()
        except Exception as e:
            log.error(f"Failed to parse item {name}, {e}")

            return

        if rarity == "frozen":
            blendColor = (148, 223, 255)
        elif rarity == "lava":
            blendColor = (234, 141, 35)
        elif rarity == "legendary":
            blendColor = (211, 120, 65)
        elif rarity == "dark":
            blendColor = (251, 34, 223)
        elif rarity == "starwars":
            blendColor = (231, 196, 19)
        elif rarity == "marvel":
            blendColor = (197, 51, 52)
        elif rarity == "dc":
            blendColor = (84, 117, 199)
        elif rarity == "icon":
            blendColor = (54, 183, 183)
        elif rarity == "shadow":
            blendColor = (113, 113, 113)
        elif rarity == "epic":
            blendColor = (177, 91, 226)
        elif rarity == "rare":
            blendColor = (73, 172, 242)
        elif rarity == "uncommon":
            blendColor = (96, 170, 58)
        elif rarity == "common":
            blendColor = (190, 190, 190)
        else:
            blendColor = (255, 255, 255)

        card = Image.new("RGBA", (310, 510))

        try:
            layer = ImageUtil.Open(
                self, f"./shopTemplates/{rarity.capitalize()}BG.png")
        except FileNotFoundError:
            log.warning(
                f"Failed to open {rarity.capitalize()}BG.png, defaulted to Common")
            layer = ImageUtil.Open(self, "./shopTemplates/CommonBG.png")
        card.paste(layer)

        icon = ImageUtil.Download(self, icon)
        if (category == "outfit") or (category == "emote"):
            icon = ImageUtil.RatioResize(self, icon, 285, 365)
        elif category == "wrap":
            icon = ImageUtil.RatioResize(self, icon, 230, 310)
        else:
            icon = ImageUtil.RatioResize(self, icon, 310, 390)
        if (category == "outfit") or (category == "emote"):
            card.paste(icon, ImageUtil.CenterX(self, icon.width, card.width), icon)
        else:
            card.paste(icon, ImageUtil.CenterX(self, icon.width, card.width, 15), icon)

        try:
            layer = ImageUtil.Open(
                self, f"./shopTemplates/{rarity.capitalize()}OV.png")
        except FileNotFoundError:
            log.warning(
                f"Failed to open {rarity.capitalize()}OV.png, defaulted to Common")
            layer = ImageUtil.Open(self, "./shopTemplates/CommonOV.png")

        card.paste(layer, layer)

        canvas = ImageDraw.Draw(card)

        vbucks = ImageUtil.Open(self, "vbucks.png")
        vbucks = ImageUtil.RatioResize(self, vbucks, 40, 40)

        font = ImageUtil.Font(self, 40)
        price = str(f"{price:,}")
        textWidth, _ = font.getsize(price)

        canvas.text(ImageUtil.CenterX(self, ((textWidth - 5) - vbucks.width), card.width, 435), price, (255, 255, 255), font=font)
        card.paste(vbucks,ImageUtil.CenterX(self, (vbucks.width + (textWidth + 5)), card.width, 438),vbucks)

        font = ImageUtil.Font(self, 40)
        itemName = name.upper().replace(" OUTFIT", "").replace(" PICKAXE", "").replace(" BUNDLE", "")

        if(category == "bundle"):
            itemName = name.upper().replace(" BUNDLE", "")

        textWidth, _ = font.getsize(itemName)

        change = 0
        if textWidth >= 270:
            # Ensure that the item name does not overflow
            font, textWidth, change = ImageUtil.FitTextX(self, itemName, 50, 250)
        canvas.text(ImageUtil.CenterX(self, textWidth, card.width, (377 + (change / 2))), itemName, (255, 255, 255), font=font)

        font = ImageUtil.Font(self, 40)
        textWidth, _ = font.getsize(f"{rarity.upper()} {category.upper()}")

        change = 0
        if textWidth >= 270:
            # Ensure that the item rarity/type does not overflow
            font, textWidth, change = ImageUtil.FitTextX(self, f"{rarity.upper()} {category.upper()}", 30, 250)
        canvas.text(ImageUtil.CenterX(self, textWidth, card.width, (450 + (change / 2))), f"", blendColor, font=font)#{rarity.upper()} {category.upper()}
        return card


if __name__ == "__main__":
    try:
        Athena.main(Athena)

    except KeyboardInterrupt:
        log.info("Exiting...")
        exit()
