import asyncio
import functools
import discord


def event_check(func):
    """Event decorator check."""
    def check(method):
        method.callback = method

        @functools.wraps(method)
        async def wrapper(*args, **kwargs):
            if await discord.utils.maybe_coroutine(func, *args, **kwargs):
                await method(*args, **kwargs)
        return wrapper
    return check


def listen_for_guilds():
    def predicate(*args):
        """Only allow message event to be called in guilds"""
        message = args[len(args) != 1]
        return message.guild is not None
    return event_check(predicate)


def in_executor(loop=None):
    """Makes a sync blocking function unblocking"""
    loop = loop or asyncio.get_event_loop()
    def inner_function(func):
        @functools.wraps(func)
        def function(*args, **kwargs):
            partial = functools.partial(func, *args, **kwargs)
            return loop.run_in_executor(None, partial)
        return function
    return inner_function
