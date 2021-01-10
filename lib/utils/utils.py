import json


def russian_plural(value: int, quantitative: list) -> str:

    """Returns a string with a declined noun"""
    if value % 100 in (11, 12, 13, 14):
        return quantitative[2]
    if value % 10 == 1:
        return quantitative[0]
    if value % 10 in (2, 3, 4):
        return quantitative[1]
    return quantitative[2]


def load_commands_from_json(cog_name:str) -> dict:
    """Returns a dictionary containing all commands of the specified cog"""

    f = open('./data/commands.json', 'r', encoding = 'utf8')
    commands = json.load(f)
    return commands[cog_name]
