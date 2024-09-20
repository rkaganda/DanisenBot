import discord
import discord.ext.commands
import sqlite3
from cogs.database import *
class Danisen(discord.ext.commands.Cog):
    characters = ["Hyde","Linne","Waldstein","Carmine","Orie","Gordeau","Merkava","Vatista","Seth","Yuzuriha","Hilda","Chaos","Nanase","Byakuya","Phonon","Mika","Wagner","Enkidu","Londrekia","Tsurugi","Kaguya","Kuon","Uzuki","Eltnum","Akatsuki"]
    players = ["player1", "player2"]

    def __init__(self, bot, database):
        self.bot = bot
        self._last_member = None
        self.database_con = database
        self.database_cur = self.database_con.cursor()
        self.database_cur.execute("CREATE TABLE IF NOT EXISTS players(discord_id, player_name, character, dan, points,   PRIMARY KEY (discord_id, character) )")

    #function assumes p1 win
    def score_update(self, p1,p2):
        if p1[3] >= p2[3] + 2:
            return
        if p1[3] >= p2[3]:
            p1[4] += 1
            if p2[3] != 1 or p2[4] != 0:
                p2[4] -= 1
        else:
            p1[4] += 2
            if p2[3] != 1 or p2[4] != 0:
                p2[4] -= 1

        if p1[4] >= 3:
            p1[3] += 1
            p1[4] = p1[4] % 3
        
        if p2[4] <= -3:
            p2[3] -= 1
            p2[4] = p2[4] % 3

    async def player_search(self, ctx: discord.AutocompleteContext):
        res = self.database_cur.execute(f"SELECT player_name FROM players")
        name_list=res.fetchall()
        return set([name[0] for name in name_list])

    async def player_autocomplete(self, ctx: discord.AutocompleteContext):
        res = self.database_cur.execute(f"SELECT player_name FROM players")
        name_list=res.fetchall()
        names = set([name[0] for name in name_list])
        return [name for name in names if (name.lower()).startswith(ctx.value.lower())]

    #registers player+char to db
    @discord.commands.slash_command(description="Register to the Danisen database!")
    async def register(self, ctx : discord.ApplicationContext, 
                    char1 : discord.Option(str, choices=characters),
                    char2 : discord.Option(str, choices=characters, required=False),
                    char3 : discord.Option(str, choices=characters, required=False)):
        char3 = char3 or ""
        char2 = char2 or ""
        player_name = ctx.author.name
        line = [ctx.author.id, player_name, char1, 1, 0]
        insert_new_player(tuple(line),self.database_cur)
        if char2:
            line[2] = char2
            insert_new_player(tuple(line),self.database_cur)
        if char3:
            line[2] = char3
            insert_new_player(tuple(line),self.database_cur)
        self.database_con.commit()
        await ctx.respond(f"""You are now registered as {player_name} with the following character/s {char1} {char2} {char3}\nif you wish to add more characters you can register multiple times!\n\nWelcome to the Danielsen!""")

    @discord.commands.slash_command(description="unregister to the Danisen database!")
    async def unregister(self, ctx : discord.ApplicationContext, 
                    char1 : discord.Option(str, choices=characters)):
        player_name = ctx.author.name
        res = self.database_cur.execute(f"DELETE FROM players WHERE discord_id={ctx.author.id} AND character='{char1}'")
        self.database_con.commit()
        await ctx.respond(f"""You have now unregistered {char1}""")

    #rank command to get discord_name's player rank, (can also ignore 2nd param for own rank)
    @discord.commands.slash_command(description="Get your character rank")
    async def rank(self, ctx : discord.ApplicationContext,
                char : discord.Option(str, choices=characters),
                discord_name :  discord.Option(str, autocomplete=player_autocomplete)):
        members = ctx.guild.members
        member = None
        for m in members:
            if discord_name.lower() == m.name.lower():
                member = m
                break
        if discord_name:
            if not member:
                await ctx.respond(f"""{discord_name} isn't a member of this server""")
                return
        else:
            member = ctx.author
        id = member.id

        res = self.database_cur.execute(f"SELECT * FROM players WHERE discord_id={id} AND character='{char}'")
        data = res.fetchone()
        if data:
            await ctx.respond(f"""{data[1]}'s rank for {char} is {data[3]} dan {data[4]} points""")
        else:
            await ctx.respond(f"""{member.name} is not registered as {char} so you have no rank...""")

    #report match score
    @discord.commands.slash_command(description="Report a match score")
    @discord.default_permissions(send_polls=True)
    async def report_match(self, ctx : discord.ApplicationContext,
                        player1 :  discord.Option(str, autocomplete=player_autocomplete),
                        char1 : discord.Option(str, choices=characters),
                        player2 :  discord.Option(str, autocomplete=player_autocomplete),
                        char2 : discord.Option(str, choices=characters),
                        winner : discord.Option(str, choices=players)):
        res = self.database_cur.execute(f"SELECT * FROM players WHERE player_name='{player1}' AND character='{char1}'")
        p1 = res.fetchone()
        res = self.database_cur.execute(f"SELECT * FROM players WHERE player_name='{player2}' AND character='{char2}'")
        p2 = res.fetchone()

        if not p1:
            await ctx.respond(f"""No player named {player1} with character {char1}""")
            return
        if not p2:
            await ctx.respond(f"""No player named {player2} with character {char2}""")
            return
        p1 = list(p1)
        p2 = list(p2)
        if (winner == "player1") :
            self.score_update(p1,p2)
            winner = player1
            loser = player2
        else:
            self.score_update(p2,p1)
            winner = player2
            loser = player1
        res = self.database_cur.execute(f"UPDATE players SET dan = {p1[3]}, points = {p1[4]} WHERE player_name='{player1}' AND character='{char1}'")
        res = self.database_cur.execute(f"UPDATE players SET dan = {p2[3]}, points = {p2[4]} WHERE player_name='{player2}' AND character='{char2}'")
        self.database_con.commit()
        await ctx.respond(f"Match has been reported as {winner}'s victory over {loser}\n{player1}'s {char1} rank is now {p1[3]} dan {p1[4]} points\n{player2}'s {char2} rank is now {p2[3]} dan {p2[4]} points")


    @discord.commands.slash_command(description="Report a match score")
    async def dan(self, ctx : discord.ApplicationContext,
                dan : discord.Option(int)):
        res = self.database_cur.execute(f"SELECT * FROM players WHERE dan={dan}")
        daniels = res.fetchall()
        outputstring = ""
        for daniel in daniels:
            outputstring += f"{daniel[1]} {daniel[2]} Dan : {daniel[3]} Points: {daniel[4]}\n"
        if not outputstring:
            outputstring = "Sorry there are no players in that dan"
        await ctx.respond(outputstring)