import discord
from discord.ext import commands
import configparser
import sqlite3
from functools import cache
from cogs.danisen import *

config = configparser.RawConfigParser()
config.read('bot.cfg')

id_dict = dict(config.items('TOKENS'))
token = id_dict['token']
test_token = id_dict['test_token']

intents = discord.Intents.default()
intents.members = True

bot = discord.Bot(intents=intents)
con = sqlite3.connect("danisen.db")

bot.add_cog(Danisen(bot,con,config))

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

async def sync_commands():
    try:
        await bot.wait_until_ready()
        # await bot.tree.sync()
        print("Commands synced successfully")
    except Exception as e:
        print(f"Error syncing commands: {e}")

bot.loop.create_task(sync_commands())

bot.run(token)
