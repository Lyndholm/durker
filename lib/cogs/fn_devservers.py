from aiohttp import ClientSession
from discord import Color, Embed
from discord.ext.commands import Cog, command
from loguru import logger

from ..utils.paginator import Paginator
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("fn_devservers")

servers = [
    "fortnite-public-service-devplaytest-prod12.ol.epicgames.com",
    "fortnite-public-service-devplaytestb-prod.ol.epicgames.com",
    "fortnite-public-service-devplaytestc-prod.ol.epicgames.com",
    "fortnite-public-service-devplaytestd-prod.ol.epicgames.com",
    "fortnite-public-service-devplayteste-prod.ol.epicgames.com",
    "fortnite-public-service-devplaytestf-prod.ol.epicgames.com",
    "fortnite-public-service-devplaytestg-prod.ol.epicgames.com",
    "fortnite-public-service-devplaytesth-prod.ol.epicgames.com",
    "fortnite-public-service-devplaytesti-prod.ol.epicgames.com",
    "fortnite-public-service-devplaytestj-prod.ol.epicgames.com",
    "fortnite-public-service-devplaytestk-prod.ol.epicgames.com",
    "fortnite-public-service-devplaytestl-prod.ol.epicgames.com",
    "fortnite-public-service-devplaytestm-prod.ol.epicgames.com",
    "fortnite-public-service-devplaytestn-prod.ol.epicgames.com",
    "fortnite-public-service-devplaytesto-prod.ol.epicgames.com",
    "fortnite-public-service-stage.ol.epicgames.com",
    "fortnite-public-service-nscert-stage.ol.epicgames.com",
    "fortnite-public-service-prod11.ol.epicgames.com",
    "fortnite.fortnite.qq.com",
    "fortnite-public-service-publictest-prod12.ol.epicgames.com",
    "fortnite-public-service-preview-prod.ol.epicgames.com",
    "fortnite-public-service-events-prod.ol.epicgames.com",
    "fortnite-public-service-reviewcn-prod.ol.epicgames.com",
    "fortnite-public-service-extqadevtesting-prod.ol.epicgames.com",
    "fortnite-public-service-extqauetesting-prod.ol.epicgames.com",
    "fortnite-public-service-bacchusplaytest-prod.ol.epicgames.com",
    "fortnite-public-service-loctesting-prod12.ol.epicgames.com",
    "fortnite-public-service-extqareleasetesting-prod.ol.epicgames.com",
    "fortnite-public-service-extqareleasetestingb-prod.ol.epicgames.com",
    "fortnite-public-service-releaseplaytest-prod.ol.epicgames.com",
    "fortnite-public-service-predeploya-prod.ol.epicgames.com",
    "fortnite-public-service-predeployb-prod.ol.epicgames.com",
    "fortnite-public-service-livebroadcasting-prod.ol.epicgames.com",
    "fortnite-public-service-livetesting-prod.ol.epicgames.com",
    "fortnite-service-livetesting.fortnite.qq.com",
    "fortnite-service-epicreleasetesting.fortnite.qq.com",
    "fortnite-service-tencentreleasetesting.fortnite.qq.com",
    "fortnite-service-securitytesting.fortnite.qq.com",
    "fortnite-service-predeploy.fortnite.qq.com",
    "fortnite-public-service-partners-prod.ol.epicgames.com",
    "fortnite-public-service-partnersstable-prod.ol.epicgames.com",
    "fortnite-public-service-ioscert-prod.ol.epicgames.com",
    "fortnite-public-service-athena-prod.ol.epicgames.com",
    "fortnite-public-service-loadtest-prod.ol.epicgames.com"
]


class FortniteDevServers(Cog, name='Fortnite Dev'):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("fn_devservers")


    @command(name=cmd["fndev"]["name"], aliases=cmd["fndev"]["aliases"],
            brief=cmd["fndev"]["brief"],
            description=cmd["fndev"]["description"],
            usage=cmd["fndev"]["usage"],
            help=cmd["fndev"]["help"],
            hidden=cmd["fndev"]["hidden"], enabled=True)
    @logger.catch
    async def fortnite_dev_servers_state_command(self, ctx, server:str="None"):
        servers_embeds = []
        if server.lower() == "stage":
            async with ClientSession() as session:
                async with session.get("https://fortnite-public-service-stage.ol.epicgames.com/fortnite/api/version") as r:
                    if r.status != 200:
                        await ctx.send(f"""```json\n{await r.text()}```""")
                        return

                    data = await r.json()

                    embed = Embed(
                        title="FortniteStageMain",
                        color=Color.orange(),
                        timestamp=ctx.message.created_at,
                        )

                    embed.add_field(name="Module", value=data["moduleName"], inline=True)
                    embed.add_field(name="Branch", value=data["branch"], inline=True)
                    embed.add_field(name="Version", value=data["version"], inline=True)
                    embed.add_field(name="Build", value=data["build"], inline=True)
                    embed.add_field(name="Build-Date", value=data["buildDate"], inline=True)
                    embed.add_field(name="Changelog #", value=data["cln"], inline=True)

                    await ctx.send(embed=embed)
                    return
        else:
            wait_embed = Embed(
                title="Fornite Dev Servers",
                color=Color.magenta(),
                description=":hourglass_flowing_sand: Сбор данных. Пожалуйста, подождите."
            )
            wait_msg = await ctx.send(embed=wait_embed)

            for url in servers:
                try:
                    async with ClientSession() as session:
                        server_url = "https://" + url + "/fortnite/api/version"
                        async with session.get(server_url) as r:
                            if r.status != 200:
                                continue

                            data = await r.json()

                            embed = Embed(
                                title="Fortnite Dev Server",
                                color=Color.orange(),
                                timestamp=ctx.message.created_at,
                                description=f"**Server:** `{url}`"
                                )

                            embed.add_field(name="Module", value=data["moduleName"], inline=True)
                            embed.add_field(name="Branch", value=data["branch"], inline=True)
                            embed.add_field(name="Version", value=data["version"], inline=True)
                            embed.add_field(name="Build", value=data["build"], inline=True)
                            embed.add_field(name="Build-Date", value=data["buildDate"], inline=True)
                            embed.add_field(name="Changelog #", value=data["cln"], inline=True)

                            servers_embeds.append(embed)

                except:
                    continue

            await wait_msg.delete()
            msg = await ctx.send(embed=servers_embeds[0])
            page = Paginator(self.bot, msg, only=ctx.author, embeds=servers_embeds)
            await page.start()


def setup(bot):
    bot.add_cog(FortniteDevServers(bot))
