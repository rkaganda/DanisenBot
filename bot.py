import discord
import configparser
import sqlite3
from database import *

characters = ["Hyde","Linne","Waldstein","Carmine","Orie","Gordeau","Merkava","Vatista","Seth","Yuzuriha","Hilda","Chaos","Nanase","Byakuya","Phonon","Mika","Wagner","Enkidu","Londrekia","Tsurugi","Kaguya","Kuon","Uzuki","Eltnum","Akatsuki"]

config = configparser.RawConfigParser()
config.read('bot.cfg')

id_dict = dict(config.items('IDS'))
token = id_dict['token']
test_token = id_dict['test_token']

intents = discord.Intents.default()
intents.members = True
bot = discord.Bot(intents=intents)


con = sqlite3.connect("danisen.db")
cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS players(discord_id, player_name, character, dan, points,   PRIMARY KEY (discord_id, character) )")

@bot.slash_command(description="Register to the Danisen google sheet!")
async def register(ctx : discord.ApplicationContext,
                   player_name : discord.Option(str, max_length=32, description="Your player name (max length is 32)"), 
                   char1 : discord.Option(str, choices=characters),
                   char2 : discord.Option(str, choices=characters, required=False),
                   char3 : discord.Option(str, choices=characters, required=False)):
    char3 = char3 or ""
    char2 = char2 or ""
    line = [ctx.author.id, player_name, char1, 1, 0]
    insert_new_player(tuple(line),cur)
    if char2:
        line[2] = char2
        insert_new_player(tuple(line),cur)
    if char3:
        line[2] = char3
        insert_new_player(tuple(line),cur)
    con.commit()
    await ctx.respond(f"""You are now registered as {player_name} with the following character/s {char1} {char2} {char3}\nif you wish to add more characters you can register multiple times!\n\nWelcome to the Danielsen!""")

@bot.slash_command(description="Get your character rank")
async def rank(ctx : discord.ApplicationContext,
               char : discord.Option(str, choices=characters),
               discord_id : discord.Option(str, required=False)):
    if discord_id:
        member = ctx.guild.get_member(int(discord_id))
        if member == None:
            await ctx.respond(f"{discord_id} is not in this server so has no rank")
            return
        id = member.id
    else:
        member = ctx.author
        id = member.id

    res = cur.execute(f"SELECT * FROM players WHERE discord_id={id} AND character='{char}'")
    data = res.fetchone()
    if data:
        await ctx.respond(f"""{data[1]}'s rank for {char} is {data[3]} dan {data[4]} points""")
    else:
        await ctx.respond(f"""{member.name} is not registered as {char} so you have no rank...""")

#function assumes p1 win
def score_update(p1,p2):
    if p1[3] >= p2[3]:
        p1[4] += 1
        if p2[3] != 1 or p2[4] != 0:
            p2[4] -= 1
    else:
        p1[4] += 2
        if p2[3] != 1 or p2[4] != 0:
            p2[4] -= 1

    if p1[4] == 3:
        p1[3] += 1
        p1[4] = 0
    
    if p2[4] == -3:
        p2[3] -= 1
        p1[4] = 0

@bot.slash_command(description="Report a match score")
@discord.default_permissions(send_polls=True)
async def report_match(ctx : discord.ApplicationContext,
                       player1 : discord.Option(str, max_length=32),
                       char1 : discord.Option(str, choices=characters),
                       player2 : discord.Option(str, max_length=32),
                       char2 : discord.Option(str, choices=characters),
                       player1_wins : discord.Option(int),
                       player1_losses : discord.Option(int)):
    if (player1_wins, player1_losses) not in [(2,0),(2,1),(0,2),(1,2)]:
        await ctx.respond(f"""Invalid score, please have the wins-losses corresponding to one of the following\n[2,0][2,1][0,2][1,2]\nRemember a match should be bo3""")
        return
    
    
    res = cur.execute(f"SELECT * FROM players WHERE player_name='{player1}' AND character='{char1}'")
    p1 = list(res.fetchone())
    res = cur.execute(f"SELECT * FROM players WHERE player_name='{player2}' AND character='{char2}'")
    p2 = list(res.fetchone())

    if not p1:
        await ctx.respond(f"""No player named {player1} with character {char1}""")
        return
    if not p2:
        await ctx.respond(f"""No player named {player2} with character {char2}""")
        return
    if (player1_wins == 2) :
        score_update(p1,p2)
    else:
        score_update(p2,p1)
    res = cur.execute(f"UPDATE players SET dan = {p1[3]}, points = {p1[4]} WHERE player_name='{player1}' AND character='{char1}'")
    res = cur.execute(f"UPDATE players SET dan = {p2[3]}, points = {p2[4]} WHERE player_name='{player2}' AND character='{char2}'")
    con.commit()
    await ctx.respond(f"Match has been reported as {player1} {player1_wins}-{player1_losses} {player2}\nRanks have been updated accordingly")

@bot.slash_command(description="Report a match score")
async def dan(ctx : discord.ApplicationContext,
              dan : discord.Option(int)):
    res = cur.execute(f"SELECT * FROM players WHERE dan={dan}")
    daniels = res.fetchall()
    outputstring = ""
    for daniel in daniels:
        outputstring += f"{daniel[1]} {daniel[2]} Dan : {daniel[3]} Points: {daniel[4]}\n"
    if not outputstring:
        outputstring = "Sorry there are no players in that dan"
    await ctx.respond(outputstring)




@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

bot.run(token)