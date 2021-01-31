import time
from io import BytesIO
from typing import Optional
from aiohttp import ClientSession
from discord import Embed, Color, File
from discord.ext.commands import Cog
from discord.ext.commands import command, is_owner, dm_only, check_any
from discord.ext.commands.errors import CheckAnyFailure

from ..utils.utils import load_commands_from_json
from ..utils.checks import is_channel, required_level
from ..utils.paginator import Paginator

cmd = load_commands_from_json("benbot")


class BenBot(Cog):
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
    async def fetch_benbot_status_command(self, ctx):
        async with ClientSession() as session:
            async with session.get('https://benbotfn.tk/api/v1/status') as r:
                if r.status != 200:
                    await ctx.send(f"""```json\n{await r.text()}```""")
                    return
                
                data = await r.json()
                await ctx.send(
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
                    )
                )


    @command(name=cmd["aes"]["name"], aliases=cmd["aes"]["aliases"], 
            brief=cmd["aes"]["brief"],
            description=cmd["aes"]["description"],
            usage=cmd["aes"]["usage"],
            help=cmd["aes"]["help"],
            hidden=cmd["aes"]["hidden"], enabled=True)
    @required_level(cmd["aes"]["required_level"])
    @is_channel(777979537795055636)
    async def fetch_fortnite_aes_command(self, ctx, version: Optional[str]):
        async with ClientSession() as session:
            async with session.get('https://benbotfn.tk/api/v1/aes', params={"version":version} if version else None) as r:
                if r.status != 200:
                    await ctx.send(f"""```json\n{await r.text()}```""")
                    return

                data = await r.json()
                aes_embeds = []
                embed = Embed(title=data.get("version", "Unknown Version"), color=Color.teal()
                            ).add_field(name="**Main Key**", value=data.get("mainKey", "Unknown"))
                aes_embeds.append(embed)

                for index, pak in enumerate(data.get("dynamicKeys", {})):
                    embed = Embed(title=pak.split("/")[-1], description=data.get("dynamicKeys", {}).get(pak, "Unknown"),
                                color=Color.teal())
                    aes_embeds.append(embed)

                message = await ctx.send(embed=aes_embeds[0])
                page = Paginator(self.bot, message, only=ctx.author, embeds=aes_embeds)
                await page.start()  


    @command(name=cmd["cosmeticinfo"]["name"], aliases=cmd["cosmeticinfo"]["aliases"], 
            brief=cmd["cosmeticinfo"]["brief"],
            description=cmd["cosmeticinfo"]["description"],
            usage=cmd["cosmeticinfo"]["usage"],
            help=cmd["cosmeticinfo"]["help"],
            hidden=cmd["cosmeticinfo"]["hidden"], enabled=True)
    async def show_fn_cosmetic_info_command(self, ctx, id: str):
        async with ClientSession() as session:
            async with session.get(f"https://benbotfn.tk/api/v1/cosmetics/br/{id}", params={"lang":"ru"}) as r:
                if r.status != 200:
                    await ctx.send(f"""```json\n{await r.text()}```""")
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
                await ctx.send(embed=embed)


    @command(name=cmd["extractasset"]["name"], aliases=cmd["extractasset"]["aliases"], 
            brief=cmd["extractasset"]["brief"],
            description=cmd["extractasset"]["description"],
            usage=cmd["extractasset"]["usage"],
            help=cmd["extractasset"]["help"],
            hidden=cmd["extractasset"]["hidden"], enabled=True)
    async def extract_fn_asset_command(self, ctx, path: str):
        async with ClientSession() as session:
            async with session.get(f"https://benbotfn.tk/api/v1/exportAsset?path={path}") as r:
                if r.status != 200:
                    await ctx.send(f"""```json\n{await r.text()}```""")
                    return

                elif r.headers.get("Content-Type", None) == "audio/ogg":
                    await ctx.send(
                        file=File(
                            fp=BytesIO(await r.read()),
                            filename=r.headers.get("filename", "audio.ogg"),
                        )
                    )
                elif r.headers.get("Content-Type", None) == "image/png":
                    await ctx.send(
                        file=File(
                            fp=BytesIO(await r.read()),
                            filename=r.headers.get("filename", "image.png"),
                        )
                    )
                elif r.headers.get("Content-Type", None) == "application/json":
                    await ctx.send(f"```json\n{await r.text()}```")
                else:
                    await ctx.send(
                        f"```Unknown Content-Type: {r.headers.get('Content-Type', 'Unknown')}```"
                    )


def setup(bot):
    bot.add_cog(BenBot(bot))
