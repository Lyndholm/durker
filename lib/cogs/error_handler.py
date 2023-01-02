
from datetime import datetime

import discord
from discord.ext import commands

from ..db import db
from ..utils.exceptions import (InForbiddenTextChannel, InsufficientLevel,
                                NotInAllowedTextChannel)
from ..utils.utils import (cooldown_timer_str, get_command_required_level,
                           get_command_text_channels)


class CommandErrorHandler(commands.Cog, name='Command error handler'):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, exc):
        if ctx.command.has_error_handler():
            return

        if isinstance(exc, commands.CommandNotFound):
            embed = discord.Embed(
                title='❗ Ошибка!',
                description=f'Команда `{ctx.message.clean_content}` не найдена.',
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False, delete_after=10)

        elif isinstance(exc, commands.CommandOnCooldown):
            embed = discord.Embed(
                title=f"{str(exc.cooldown.type).split('.')[-1]} cooldown",
                description=f"Команда на откате. Ожидайте {cooldown_timer_str(exc.retry_after)}",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False, delete_after=15)

        elif isinstance(exc, commands.DisabledCommand):
            embed = discord.Embed(
                title='❗ Ошибка!',
                description=f"Команда `{ctx.command}` отключена.",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False)

        elif isinstance(exc, commands.NoPrivateMessage):
            try:
                embed = discord.Embed(
                    title='❗ Ошибка!',
                    description=f"Команда `{ctx.command}` не может быть использована в личных сообщениях.",
                    color=discord.Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False)
            except discord.errors.HTTPException:
                pass

        elif isinstance(exc, commands.PrivateMessageOnly):
            embed = discord.Embed(
                title='❗ Ошибка!',
                description=f"Команда `{ctx.command}` работает только в личных сообщениях. Она не может быть использована на сервере.",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False, delete_after=15)

        elif isinstance(exc, commands.MissingPermissions):
            embed = discord.Embed(
                title='❗ MissingPermissions',
                description=f"Недостаточно прав для выполнения действия.",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False, delete_after=15)

        elif isinstance(exc, discord.errors.Forbidden):
            embed = discord.Embed(
                title='❗ Forbidden',
                description=f"Недостаточно прав для выполнения действия.",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False, delete_after=15)

        elif isinstance(exc, discord.errors.HTTPException):
            embed = discord.Embed(
                title='❗ Ошибка!',
                description=f"Не удалось отправить сообщение. Возможно, превышен лимит символов "
                            "или размер файла больше 8 МБ.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

        elif isinstance(exc, commands.MaxConcurrencyReached):
            embed = discord.Embed(
                title='❗ Внимание!',
                description=f"Команда `{ctx.command}` уже запущена.",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False)

        elif isinstance(exc, commands.EmojiNotFound):
            embed = discord.Embed(
                title='❗ Ошибка!',
                description='Указанные эмодзи не найдены. '
                            'Возможно, вы указали глобальный эмодзи или эмодзи, '
                            'которого нет на этом сервере.',
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False)

        elif isinstance(exc, commands.MissingRequiredArgument):
            if str(ctx.command) == 'knb':
                embed = discord.Embed(
                    title='❗ Внимание!',
                    description=f'Укажите, что вы выбрали: камень, ножницы или бумагу.\n' \
                                f'`{ctx.command.usage}`',
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed, delete_after=15)
            elif str(ctx.command) == '8ball':
                embed = discord.Embed(
                    title='❗ Внимание!',
                    description=f"Пожалуйста, укажите вопрос.",
                    color=discord.Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=15)
            elif str(ctx.command) == 'randint':
                embed = discord.Embed(
                    title='❗ Внимание!',
                    description=f"Пожалуйста, укажите корректный диапазон **целых** чисел.",
                    color=discord.Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=15)
            else:
                embed = discord.Embed(
                    title='❗ Внимание!',
                    description=f"Пропущен один или несколько параметров. Параметры команды можно узнать в help меню.",
                    color=discord.Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False)

        elif isinstance(exc, InsufficientLevel):
            level = await get_command_required_level(ctx.command)
            member_level = db.fetchone(['level'], 'leveling', 'user_id', ctx.author.id)[0]
            embed = discord.Embed(
                title='🔒 Недостаточный уровень!',
                description=f"Команда `{ctx.command.name}` требует наличия **{level}** уровня " \
                            f"и выше.\nВаш текущий уровень: **{member_level}**.",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False)

        elif isinstance(exc, NotInAllowedTextChannel) or isinstance(exc, InForbiddenTextChannel):
            txt = await get_command_text_channels(ctx.command)
            embed = discord.Embed(
                title='⚠️ Неправильный канал!',
                description=f"Команда `{ctx.command.name}` {txt.lower()}",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False)

        elif isinstance(exc, commands.CheckFailure) or isinstance(exc, commands.CheckAnyFailure):
            embed = discord.Embed(
                title='❗ Ошибка!',
                description=f"{ctx.author.mention}\nНевозможно выполнить указанную команду."
                            "\nВозможно, у вас отсутствуют права на выполнение запрошенного метода.",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False, delete_after=15)

        else:
            try:
                if hasattr(ctx.command, 'on_error'):
                    embed = discord.Embed(
                        title="Error.",
                        description="Something went wrong, an error occured.\nCheck logs.",
                        timestamp=datetime.utcnow(),
                        color=discord.Color.red()
                    )
                    await self.bot.logs_channel.send(embed=embed)
                else:
                    embed = discord.Embed(
                        title=f'Ошибка при выполнении команды {ctx.command}.',
                        description=f'`{ctx.command.signature if ctx.command.signature else None}`\n{exc}',
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    if isinstance(ctx.channel, discord.DMChannel):
                        embed.add_field(name="Additional info:", value="Exception occured in DMChannel.")
                    await self.bot.logs_channel.send(embed=embed)
            except:
                embed = discord.Embed(
                    title=f'Ошибка при выполнении команды {ctx.command}.',
                    description=f'`{ctx.command.signature if ctx.command.signature else None}`\n{exc}',
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                if isinstance(ctx.channel, discord.DMChannel):
                    embed.add_field(name="Additional info:", value="Exception occured in DMChannel.")
                await self.bot.logs_channel.send(embed=embed)
            finally:
                raise exc

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("error_handler")


async def setup(bot):
    await bot.add_cog(CommandErrorHandler(bot))
