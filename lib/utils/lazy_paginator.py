import asyncio
import discord


async def paginate(ctx, input_):
    try:
        pages = await ctx.send(embed=input_[0])
    except (AttributeError, TypeError):
        return await ctx.send(embed=input_)

    if len(input_) == 1:
        return

    current = 0

    r = ['\U000023ee', '\U000025c0', '\U000025b6',
         '\U000023ed', '\U0001f522', '\U000023f9']
    for x in r:
        await pages.add_reaction(x)

    paging = True
    while paging:
        def check(r_, u_):
            return u_ == ctx.author and r_.message.id == pages.id and str(r_.emoji) in r

        done, pending = await asyncio.wait([ctx.bot.wait_for('reaction_add', check=check, timeout=120),
                                            ctx.bot.wait_for('reaction_remove', check=check, timeout=120)],
                                           return_when=asyncio.FIRST_COMPLETED)
        try:
            reaction, user = done.pop().result()
        except asyncio.TimeoutError:
            try:
                await pages.clear_reactions()
            except discord.Forbidden:
                await pages.delete()
            finally:
                for future in done:
                    future.exception()
                paging = False
                return

        for future in pending:
            future.cancel()
        else:
            if str(reaction.emoji) == r[2]:
                current += 1
                if current == len(input_):
                    current = 0
                    try:
                        await pages.remove_reaction(r[2], ctx.author)
                    except discord.Forbidden:
                        pass
                    await pages.edit(embed=input_[current])

                await pages.edit(embed=input_[current])
            elif str(reaction.emoji) == r[1]:
                current -= 1
                if current == 0:
                    try:
                        await pages.remove_reaction(r[1], ctx.author)
                    except discord.Forbidden:
                        pass

                    await pages.edit(embed=input_[len(input_) - 1])

                await pages.edit(embed=input_[current])
            elif str(reaction.emoji) == r[0]:
                current = 0
                try:
                    await pages.remove_reaction(r[0], ctx.author)
                except discord.Forbidden:
                    pass

                await pages.edit(embed=input_[current])

            elif str(reaction.emoji) == r[3]:
                current = len(input_) - 1
                try:
                    await pages.remove_reaction(r[3], ctx.author)
                except discord.Forbidden:
                    pass

                await pages.edit(embed=input_[current])

            elif str(reaction.emoji) == r[4]:
                m = await ctx.send(f'Введите номер желаемой страницы: 1-{len(input_)}')

                def pager(m_):
                    try:
                        return m_.author == ctx.author and m_.channel == ctx.channel and int(m_.content) > 1 <= len(input_)
                    except ValueError:
                        return

                try:
                    message = await ctx.bot.wait_for('message', check=pager, timeout=60)
                    msg = int((message).content)
                    if ctx.guild:
                        await message.delete()
                    await m.delete()
                except asyncio.TimeoutError:
                    return await m.delete()
                current = msg - 1
                try:
                    await pages.remove_reaction(r[4], ctx.author)
                except discord.Forbidden:
                    pass
                try:
                    await pages.edit(embed=input_[current])
                except IndexError:
                    pass
            else:
                try:
                    await pages.clear_reactions()
                except discord.Forbidden:
                    await pages.delete()

                paging = False
