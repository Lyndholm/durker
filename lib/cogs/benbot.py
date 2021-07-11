import shlex
from argparse import ArgumentParser
from datetime import datetime
from io import BytesIO
from typing import Optional

from aiohttp import ClientSession
from discord import Color, Embed, File
from discord.ext.commands import (BucketType, Cog, command, cooldown, dm_only,
                                  guild_only, is_owner)
from loguru import logger

from ..utils.checks import is_channel, required_level
from ..utils.constants import CONSOLE_CHANNEL
from ..utils.paginator import Paginator
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("benbot")


class Arguments(ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


class BenBot(Cog, name='Fortnite API 1'):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("benbot")

    @command(name=cmd["benbotstatus"]["name"], aliases=cmd["benbotstatus"]["aliases"],
            brief=cmd["benbotstatus"]["brief"],
            description=cmd["benbotstatus"]["description"],
            usage=cmd["benbotstatus"]["usage"],
            help=cmd["benbotstatus"]["help"],
            hidden=cmd["benbotstatus"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def fetch_benbot_status_command(self, ctx):
        async with ClientSession() as session:
            async with session.get('https://benbot.app/api/v1/status') as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                    return

                data = await r.json()
                await ctx.reply(
                    embed=Embed(title="BenBot Status", color=Color.random())
                    .add_field(
                        name="Version",
                        value=f"`{data.get('currentFortniteVersion', 'Unknown')}`",
                        inline=False,
                    )
                    .add_field(
                        name="CDN Version",
                        value=f"`{data.get('currentCdnVersion', 'Unknown')}`",
                        inline=False,
                    )
                    .add_field(
                        name="Pak Count",
                        value=f"`{len(data.get('mountedPaks', []))}/{data.get('totalPakCount', 'Unknown')}`",
                        inline=False,
                    ),
                    mention_author=False
                )


    @command(name=cmd["aes"]["name"], aliases=cmd["aes"]["aliases"],
            brief=cmd["aes"]["brief"],
            description=cmd["aes"]["description"],
            usage=cmd["aes"]["usage"],
            help=cmd["aes"]["help"],
            hidden=cmd["aes"]["hidden"], enabled=True)
    @is_channel(CONSOLE_CHANNEL)
    @required_level(cmd["aes"]["required_level"])
    @guild_only()
    @cooldown(cmd["aes"]["cooldown_rate"], cmd["aes"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def fetch_fortnite_aes_command(self, ctx, version: Optional[str]):
        async with ClientSession() as session:
            async with session.get('https://benbot.app/api/v1/aes', params={"version":version} if version else None) as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                    return

                data = await r.json()
                aes_embeds = []
                embed = Embed(title=data.get("version", "Unknown Version"), color=Color.teal()
                            ).add_field(name="**Main Key**", value=data.get("mainKey", "Unknown"))
                aes_embeds.append(embed)

                for pak in data.get("dynamicKeys", {}):
                    embed = Embed(title=pak.split("/")[-1], description=data.get("dynamicKeys", {}).get(pak, "Unknown"),
                                color=Color.teal())
                    aes_embeds.append(embed)

                message = await ctx.reply(embed=aes_embeds[0], mention_author=False)
                page = Paginator(self.bot, message, only=ctx.author, embeds=aes_embeds)
                await page.start()


    @command(name=cmd["cosmeticinfo"]["name"], aliases=cmd["cosmeticinfo"]["aliases"],
            brief=cmd["cosmeticinfo"]["brief"],
            description=cmd["cosmeticinfo"]["description"],
            usage=cmd["cosmeticinfo"]["usage"],
            help=cmd["cosmeticinfo"]["help"],
            hidden=cmd["cosmeticinfo"]["hidden"], enabled=True)
    @required_level(cmd["cosmeticinfo"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @logger.catch
    async def show_fn_cosmetic_info_command(self, ctx, id: str):
        async with ClientSession() as session:
            async with session.get(f"https://benbot.app/api/v1/cosmetics/br/{id}", params={"lang":"ru"}) as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                    return

                cosmetic = await r.json()
                embed = Embed(
                    title=cosmetic.get("name", id),
                    description=f"{cosmetic.get('description', '')}\n{cosmetic.get('setText', 'Not part of any set.')}",
                    color=Color.random()
                ).add_field(name="Редкость", value=cosmetic.get("rarity", "Unknown"), inline=True)
                if type(cosmetic.get("series", "")) == dict:
                    embed.add_field(
                        name="Набор", value=cosmetic["series"].get("name", "None"), inline=True
                    )
                else:
                    embed.add_field(name="Series", value="None", inline=True)
                embed.add_field(
                    name="Backend Type",
                    value=cosmetic.get("backendType", "Unknown"),
                    inline=True,
                ).add_field(
                    name="Gameplay Tags",
                    value="```" + "\n".join(cosmetic.get("gameplayTags", "None")) + "```",
                    inline=False,
                ).add_field(
                    name="Path", value="`" + cosmetic.get("path", "Unknown") + "`", inline=False
                )
                if type(cosmetic.get("icons", "")) == dict:
                    if cosmetic["icons"].get("icon", None) is not None:
                        embed.set_thumbnail(url=cosmetic["icons"]["icon"])
                    if cosmetic["icons"].get("featured", None) is not None:
                        embed.set_image(url=cosmetic["icons"]["featured"])
                await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["extractasset"]["name"], aliases=cmd["extractasset"]["aliases"],
            brief=cmd["extractasset"]["brief"],
            description=cmd["extractasset"]["description"],
            usage=cmd["extractasset"]["usage"],
            help=cmd["extractasset"]["help"],
            hidden=cmd["extractasset"]["hidden"], enabled=True)
    @required_level(cmd["extractasset"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @logger.catch
    async def extract_fn_asset_command(self, ctx, path: str, *, args: str = None):
        if args is not None:
            parser = Arguments(add_help=False, allow_abbrev=False)
            parser.add_argument('-lang', nargs='+')
            parser.add_argument('-rawIcon', nargs='+')
            parser.add_argument('-noFeatured', nargs='+')
            parser.add_argument('-noVariants', nargs='+')
            parser.add_argument('-priceDaily', nargs='+')
            parser.add_argument('-priceFeatured', nargs='+')

            try:
                args = parser.parse_args(shlex.split(args))
            except Exception as e:
                await ctx.reply(str(e), mention_author=False)

            parameter = ""

            if args.lang:
                parameter += f"&lang={args.lang[0].lower()}"
            else:
                parameter += "&lang=ru"

            if args.rawIcon:
                parameter += f"&rawIcon={args.rawIcon[0].lower()}"

            if args.noFeatured:
                parameter += f"&noFeatured={args.noFeatured[0].lower()}"

            if args.noVariants:
                parameter += f"&noVariants={args.noVariants[0].lower()}"

            if args.priceDaily:
                parameter += f"&priceDaily={args.priceDaily[0].lower()}"

            if args.priceFeatured:
                parameter += f"&priceFeatured={args.priceFeatured[0].lower()}"

        else:
            parameter = "&lang=ru"

        async with ClientSession() as session:
            async with session.get(f"https://benbot.app/api/v1/exportAsset?path={path}{parameter}") as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                    return

                elif r.headers.get("Content-Type", None) == "audio/ogg":
                    await ctx.reply(
                        file=File(
                            fp=BytesIO(await r.read()),
                            filename=r.headers.get("filename", "audio.ogg")
                        ),
                        mention_author=False
                    )
                elif r.headers.get("Content-Type", None) == "image/png":
                    await ctx.reply(
                        file=File(
                            fp=BytesIO(await r.read()),
                            filename=r.headers.get("filename", "image.png"),
                        ),
                        mention_author=False
                    )
                elif r.headers.get("Content-Type", None) == "application/json":
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                else:
                    await ctx.reply(
                        f"```Unknown Content-Type: {r.headers.get('Content-Type', 'Unknown')}```",
                        mention_author=False
                    )


    @command(name=cmd["shopsections"]["name"], aliases=cmd["shopsections"]["aliases"],
            brief=cmd["shopsections"]["brief"],
            description=cmd["shopsections"]["description"],
            usage=cmd["shopsections"]["usage"],
            help=cmd["shopsections"]["help"],
            hidden=cmd["shopsections"]["hidden"], enabled=True)
    @required_level(cmd["shopsections"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["shopsections"]["cooldown_rate"], cmd["shopsections"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def display_fortnite_section_store_command(self, ctx, lang: str = 'ru'):
        async with ClientSession() as session:
            async with session.get(f'https://fn-api.com/api/shop/sections?lang={lang}') as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                    return
                data = await r.json()

        time = ""
        j = data['data']['timestamp'].split("T")
        i = j[0].split("-")
        time += f"{i[2]}.{i[1]}.{i[0]} {j[1][:-1]}"

        embed = Embed(
            title="Разделы магазина предметов",
            color=Color.gold(),
            timestamp=datetime.utcnow(),
            description=f'Актуально до: {time} UTC.\n\n'
        )

        var = ""
        for section in data['data']['sections']:
            name = section["name"] if section["name"] else section["id"]
            var += f'— **{name}**'
            if section['quantity'] > 1:
                var += f' (x{section["quantity"]})\n'
            else:
                var += '\n'

        embed.description += var
        await ctx.reply(embed=embed, mention_author=False)


def setup(bot):
    bot.add_cog(BenBot(bot))
