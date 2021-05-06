import json
import aiofiles
from discord import Embed, Color, Member
from discord.ext.commands import Cog, BucketType
from discord.ext.commands import command, cooldown
from discord.ext.commands import check_any, is_owner, guild_only, dm_only
from discord.ext.commands.errors import MissingRequiredArgument
from discord.channel import DMChannel

from random import randint, choice
from aiohttp import ClientSession
from asyncio import sleep


from ..utils import checks
from ..utils.utils import load_commands_from_json


cmd = load_commands_from_json("fun")


class Fun(Cog, name='Развлечения'):
    def __init__(self, bot):
        self.bot = bot
        self.hug_gifs = ["https://media4.giphy.com/media/PHZ7v9tfQu0o0/giphy.gif",
                        "https://i.pinimg.com/originals/f2/80/5f/f2805f274471676c96aff2bc9fbedd70.gif",
                        "https://media.tenor.com/images/b6d0903e0d54e05bb993f2eb78b39778/tenor.gif",
                        "https://thumbs.gfycat.com/AlienatedFearfulJanenschia-small.gif",
                        "https://i.imgur.com/r9aU2xv.gif",
                        "https://25.media.tumblr.com/2a3ec53a742008eb61979af6b7148e8d/tumblr_mt1cllxlBr1s2tbc6o1_500.gif",
                        "https://media.tenor.com/images/ca88f916b116711c60bb23b8eb608694/tenor.gif"]

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("fun")

    @command(name=cmd["hug"]["name"], aliases=cmd["hug"]["aliases"],
            brief=cmd["hug"]["brief"],
            description=cmd["hug"]["description"],
            usage=cmd["hug"]["usage"],
            help=cmd["hug"]["help"],
            hidden=cmd["hug"]["hidden"], enabled=True)
    async def hug_command(self, ctx, *, member: Member):
        await ctx.message.delete()
        async with ClientSession() as session:
            async with session.get('https://some-random-api.ml/animu/hug') as r:
                if r.status == 200:
                    data = await r.json()
                    hug_gif_url = data["link"]
                else:
                    hug_gif_url = choice(self.hug_gifs)

        embed = Embed(title = f'**Обнимашки!**',description = f'{ctx.author.mention} обнял(-а) {member.mention} :heart::sparkles:', color=ctx.author.color)
        embed.set_image(url=hug_gif_url)
        await ctx.send(embed=embed, delete_after=180)


    @command(name=cmd["coin"]["name"], aliases=cmd["coin"]["aliases"],
            brief=cmd["coin"]["brief"],
            description=cmd["coin"]["description"],
            usage=cmd["coin"]["usage"],
            help=cmd["coin"]["help"],
            hidden=cmd["coin"]["hidden"], enabled=True)
    @checks.required_level(cmd["coin"]["required_level"])
    @check_any(checks.is_any_channel([777979537795055636, 796439346344493107, 708601604353556491]), dm_only())
    async def drop_coin_command(self, ctx):
        robot_choice = choice(["орёл", "решка"])

        embed = Embed(title=":coin: Орёл или решка", description = "Подбрасываем монетку....", color=Color.red())
        message = await ctx.send(embed=embed)

        await sleep(3)

        embed_new = embed = Embed(title=":coin: Орел или решка", description = f"Выпало: {'**Орёл**' if robot_choice == 'орёл' else '**Решка**'}", color=Color.green(), timestamp=ctx.message.created_at)
        embed_new.set_footer(text=f'{ctx.author.name}', icon_url=ctx.author.avatar_url)
        await message.edit(embed=embed_new)


    @command(name=cmd["saper"]["name"], aliases=cmd["saper"]["aliases"],
            brief=cmd["saper"]["brief"],
            description=cmd["saper"]["description"],
            usage=cmd["saper"]["usage"],
            help=cmd["saper"]["help"],
            hidden=cmd["saper"]["hidden"], enabled=True)
    async def saper_command(self, ctx):
        await ctx.message.delete()

        r_list = ['🟩', '🟧', '🟥']

        rows = None
        columns = None

        embed = Embed(title="Выберите сложность:", description=f"{r_list[0]} — Легко\n{r_list[1]} — Средне\n{r_list[2]} — Сложно", color=Color.random())
        msg = await ctx.send(embed=embed)
        for r in r_list:
            await msg.add_reaction(r)
        try:
            react, user = await self.bot.wait_for('reaction_add', timeout=45.0, check=lambda react,
                                                                                             user: user == ctx.author and react.message.channel == ctx.channel and react.emoji in r_list)
        except Exception:
            await msg.delete()
            await ctx.send(f"{ctx.author.mention}, время на выбор сложности вышло.", delete_after=20)
        else:
            if str(react.emoji) == r_list[0]:
                columns = 4
                rows = 4
                await msg.clear_reactions()
            elif str(react.emoji) == r_list[1]:
                columns = 8
                rows = 8
                await msg.clear_reactions()
            elif str(react.emoji) == r_list[2]:
                columns = 12
                rows = 12
                await msg.clear_reactions()
            else:
                await msg.delete()
                await ctx.send('Неверная реакция!', delete_after=10.0)

        try:
            bombs = columns * rows - 1
            bombs = bombs / 2.5
            bombs = round(randint(3, round(bombs)))

            columns = int(columns)
            rows = int(rows)
            bombs = int(bombs)

            grid = [[0 for num in range(columns)] for num in range(rows)]

            loop_count = 0
            while loop_count < bombs:
                x = randint(0, columns - 1)
                y = randint(0, rows - 1)

                if grid[y][x] == 0:
                    grid[y][x] = 'B'
                    loop_count = loop_count + 1

                if grid[y][x] == 'B':
                    pass

            pos_x = 0
            pos_y = 0
            while pos_x * pos_y < columns * rows and pos_y < rows:

                adj_sum = 0

                for (adj_y, adj_x) in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)]:

                    try:
                        if grid[adj_y + pos_y][adj_x + pos_x] == 'B' and adj_y + pos_y > -1 and adj_x + pos_x > -1:
                            adj_sum = adj_sum + 1
                    except Exception:
                        pass

                if grid[pos_y][pos_x] != 'B':
                    grid[pos_y][pos_x] = adj_sum

                if pos_x == columns - 1:
                    pos_x = 0
                    pos_y = pos_y + 1
                else:
                    pos_x = pos_x + 1

            not_final = []

            for the_rows in grid:
                not_final.append(''.join(map(str, the_rows)))

            not_final = '\n'.join(not_final)

            not_final = not_final.replace('0', '||:zero:||')
            not_final = not_final.replace('1', '||:one:||')
            not_final = not_final.replace('2', '||:two:||')
            not_final = not_final.replace('3', '||:three:||')
            not_final = not_final.replace('4', '||:four:||')
            not_final = not_final.replace('5', '||:five:||')
            not_final = not_final.replace('6', '||:six:||')
            not_final = not_final.replace('7', '||:seven:||')
            not_final = not_final.replace('8', '||:eight:||')
            final = not_final.replace('B', '||:bomb:||')

            percentage = columns * rows
            percentage = bombs / percentage
            percentage = 100 * percentage
            percentage = round(percentage, 2)

            embed = Embed(description=final,color=Color.random())
            embed.add_field(name='Всего клеток :', value=columns * rows, inline=False)
            embed.add_field(name='Количество столбцов :', value=columns,inline=True)
            embed.add_field(name='Количество строк:', value=rows, inline=True)
            embed.add_field(name='Количество бомб:', value=bombs, inline=True)
            await msg.edit(embed=embed)
        except TypeError:
            pass


    @command(name=cmd["flags"]["name"], aliases=cmd["flags"]["aliases"],
            brief=cmd["flags"]["brief"],
            description=cmd["flags"]["description"],
            usage=cmd["flags"]["usage"],
            help=cmd["flags"]["help"],
            hidden=cmd["flags"]["hidden"], enabled=True)
    async def guess_flags_command(self, ctx):
        event_members = {}
        async with aiofiles.open('./data/country_flags.json', mode='r', encoding = 'utf8') as f:
            flags = json.loads(await f.read())
            count = 1
            flags_list = []
            while count <= 10:
                otvet = choice(flags['Флаги'])
                if otvet in flags_list:
                    pass
                elif otvet not in flags_list:
                    flags_list.append(otvet)
                    embed = Embed(title = f"Флаг {count}", color=Color.random())
                    embed.set_image(url = otvet['url'])
                    await ctx.send(embed=embed)
                    def check(m):
                        answers = []
                        answers.append(otvet['answer'])
                        try:
                            answers.append(otvet['alias'])
                        except KeyError:
                            pass
                        return any([m.content.lower() == answer.lower() for answer in answers]) and m.channel == ctx.channel

                    try:
                        msg = await self.bot.wait_for('message', timeout=600.0,  check=check)
                        if str(msg.author.id) not in event_members:
                            event_members[str(msg.author.id)] = {}
                            event_members[str(msg.author.id)]["score"] = 1
                        elif str(msg.author.id) in event_members:
                            event_members[str(msg.author.id)]["score"] += 1
                        em = Embed(title = "Верно!", color=Color.green())
                        em.set_thumbnail(url=otvet['url'])
                        em.add_field(name = "Правильный ответ:",value = f"{msg.content.title()}")
                        em.add_field(name = "Ответил:", value = f"{msg.author.mention}")
                        await ctx.send(embed = em)
                        count = count + 1
                        await sleep(1)
                        if count == 11:
                            e = Embed(title = "Конец игры!", description = f"Таблица лидеров:", color=Color.random())
                            leaders = sorted(event_members, key=lambda score: event_members[score]['score'], reverse=True)
                            position = 1
                            for leader in leaders:
                                leader = self.bot.get_user(int(leaders[position-1]))
                                leader_score = event_members[str(leader.id)]['score']
                                e.add_field(name=f"{position} место:", value=f"{leader.mention} | Очки: **{leader_score}**",inline=False)
                                position += 1
                            await ctx.send(embed = e)
                    except:
                        await ctx.send("Время на угадывание флага вышло, игра окончена.")
                        if count > 1:
                            e = Embed(title = "Конец игры!", description = f"Таблица лидеров:", color=Color.random())
                            leaders = sorted(event_members, key=lambda score: event_members[score]['score'], reverse=True)
                            position = 1
                            for leader in leaders:
                                leader = self.bot.get_user(int(leaders[position-1]))
                                leader_score = event_members[str(leader.id)]['score']
                                e.add_field(name=f"{position} место:", value=f"{leader.mention} | Очки: **{leader_score}**",inline=False)
                                position += 1
                            await ctx.send(embed = e)
                        return


    @command(name=cmd["knb"]["name"], aliases=cmd["knb"]["aliases"],
            brief=cmd["knb"]["brief"],
            description=cmd["knb"]["description"],
            usage=cmd["knb"]["usage"],
            help=cmd["knb"]["help"],
            hidden=cmd["knb"]["hidden"], enabled=True)
    async def stone_scissors_paper_command(self, ctx, item: str):
        await ctx.message.delete()
        robot = ['Камень', 'Ножницы', 'Бумага']
        stone_list = ["stone", "камень","к"]
        paper_list = ["paper", "бумага", "б"]
        scissors_list = ["scissors", "ножницы","н"]

        out = {
            "icon": None,
            "value": None,
            "img": None
            }

        robot_choice = choice(robot)

        win_list = ["Вы выиграли! :smiley:","Вы проиграли :pensive:", "Ничья! :cowboy:"]

        if item.lower() in stone_list:
            if robot_choice == 'Ножницы':
                win = win_list[0]
                out["icon"] = ":scissors:"
            elif robot_choice == 'Бумага':
                win = win_list[1]
                out["icon"] = ":newspaper:"
            else:
                win = win_list[2]
                out["icon"] = ":rock:"

        elif item.lower() in paper_list:
            if robot_choice == 'Камень':
                win = win_list[0]
                out["icon"] = ":rock:"
            elif robot_choice == 'Ножницы':
                win = win_list[1]
                out["icon"] = ":scissors:"
            else:
                win = win_list[2]
                out["icon"] = ":newspaper:"

        elif item.lower() in scissors_list:
            if robot_choice == 'Бумага':
                win = win_list[0]
                out["icon"] = ":newspaper:"
            elif robot_choice == 'Камень':
                win = win_list[1]
                out["icon"] = ":rock:"
            else:
                win = win_list[2]
                out["icon"] = ":scissors:"
        else:
            await ctx.send("Ошибка!", delete_after = 20)
            return

        if win == win_list[0]:
            out["img"] = "https://image.flaticon.com/icons/png/512/445/445087.png"
        elif win == win_list[1]:
            out["img"] = "https://cdn.discordapp.com/attachments/774698479981297664/774700936958312468/placeholder.png"
        else:
            out["img"] = "https://cdn.discordapp.com/attachments/774698479981297664/774700936958312468/placeholder.png"

        embed = Embed(title="Результат игры", description = win, colour=Color.random(), timestamp=ctx.message.created_at)
        embed.add_field(name="Выбор бота:", value=robot_choice, inline=True)
        embed.add_field(name=f"Выбор {ctx.author.display_name}:", value=item.title(), inline=True)
        embed.set_thumbnail(url=out["img"])
        embed.set_footer(icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @stone_scissors_paper_command.error
    async def stone_scissors_paper_command_error(self, ctx, exc):
        if isinstance(exc, MissingRequiredArgument):
            embed = Embed(title=':exclamation: Внимание!', description =f"Укажите, что вы выбрали: камень, ножницы или бумагу.\n`{ctx.command} {ctx.command.usage}`", color= Color.red())
            await ctx.send(embed=embed, delete_after = 20)


    @command(name=cmd["8ball"]["name"], aliases=cmd["8ball"]["aliases"],
            brief=cmd["8ball"]["brief"],
            description=cmd["8ball"]["description"],
            usage=cmd["8ball"]["usage"],
            help=cmd["8ball"]["help"],
            hidden=cmd["8ball"]["hidden"], enabled=True)
    @guild_only()
    async def magic_ball_command(self, ctx, *, question: str):
        posible_answers = {
            "affirmative": {
                "color": Color.green(),
                "answers": [
                    "**Бесспорно**", "**Предрешено**", "**Никаких сомнений**", "**Определённо да**", "**Можешь быть уверен в этом**",
                    "**Мне кажется — «да»**", "**Вероятнее всего**", "**Хорошие перспективы**", "**Знаки говорят — «да»**", "**Да**"
                ]
            },
            "non-committal":{
                "color": Color.gold(),
                "answers": [
                    "**Пока не ясно, попробуй снова**", "**Спроси позже**", "**Лучше не рассказывать**", "**Сейчас нельзя предсказать**",
                    "**Сконцентрируйся и спроси опять**"
                ]
            },
            "negative":{
                "color": Color.red(),
                "answers": [
                    "**Даже не думай**", "**Мой ответ — «нет»**", "**По моим данным — «нет»**", "**Перспективы не очень хорошие**",
                    "**Весьма сомнительно**"
                ]
            }
        }

        answer_category = choice(list(posible_answers.keys()))

        if question.strip()[-1] == "?":
            embed = Embed(description=choice(posible_answers[answer_category]["answers"]), color=posible_answers[answer_category]["color"])
            embed.set_author(name="Магический шар", icon_url="https://upload.wikimedia.org/wikipedia/commons/e/eb/Magic_eight_ball.png")
            await ctx.send(embed=embed)
        else:
            await ctx.send("Это не вопрос.")


    @magic_ball_command.error
    async def magic_ball_command_error(self, ctx, exc):
        if isinstance(exc, MissingRequiredArgument):
            embed = Embed(title=':exclamation: Внимание!', description =f"Пожалуйста, укажите вопрос.", color = Color.red())
            await ctx.send(embed=embed, delete_after = 30)


    @command(name=cmd["randint"]["name"], aliases=cmd["randint"]["aliases"],
            brief=cmd["randint"]["brief"],
            description=cmd["randint"]["description"],
            usage=cmd["randint"]["usage"],
            help=cmd["randint"]["help"],
            hidden=cmd["randint"]["hidden"], enabled=True)
    async def randint_command(self, ctx, a: int, b: int):
        embed = Embed(title="Генератор случайных чисел", description=f"Случайное целое число: **{randint(a,b)}**", color=Color.random())
        await ctx.send(embed=embed)

    @randint_command.error
    async def randint_command_error(self, ctx, exc):
        if isinstance(exc, MissingRequiredArgument):
            embed = Embed(title=':exclamation: Внимание!', description =f"Пожалуйста, укажите корректный диапазон **целых** чисел.", color = Color.red())
            await ctx.send(embed=embed, delete_after = 30)


def setup(bot):
    bot.add_cog(Fun(bot))
