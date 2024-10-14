import discord, sqlite3, asyncio
from discord.ext import commands, pages
from cogs.database import *
from cogs.custom_views import *
class Danisen(commands.Cog):
    characters = ["Hyde","Linne","Waldstein","Carmine","Orie","Gordeau","Merkava","Vatista","Seth","Yuzuriha","Hilda","Chaos","Nanase","Byakuya","Phonon","Mika","Wagner","Enkidu","Londrekia","Tsurugi","Kaguya","Kuon","Uzuki","Eltnum","Akatsuki"]
    players = ["player1", "player2"]
    dan_colours = [discord.Colour.from_rgb(255,255,255), discord.Colour.yellow(), discord.Colour.orange(),
                   discord.Colour.dark_green(), discord.Colour.purple(), discord.Colour.blue(), discord.Colour.from_rgb(120,63,4)]
    total_dans = 7

    def __init__(self, bot, database):
        self.bot = bot
        self._last_member = None
        self.database_con = database
        self.database_con.row_factory = sqlite3.Row
        self.database_cur = self.database_con.cursor()
        self.database_cur.execute("CREATE TABLE IF NOT EXISTS players(discord_id, player_name, character, dan, points,   PRIMARY KEY (discord_id, character) )")
        self.dead_daniels = { dan:0 for dan in range(self.total_dans) }
        self.daniel_queues = { dan:asyncio.Queue() for dan in range(self.total_dans) }
        self.matchmaking_queue = asyncio.Queue()
        self.max_active_matches = 3
        self.cur_active_matches = 0
        self.in_queue = {}
    #function assumes p1 win
    def score_update(self, p1,p2):
        rankdown = False
        rankup = False
        if p1[0] >= p2[0] + 2:
            return 
        if p1[0] >= p2[0]:
            p1[1] += 1
            if p2[0] != 1 or p2[1] != 0:
                p2[1] -= 1
        else:
            p1[1] += 2
            if p2[0] != 1 or p2[1] != 0:
                p2[1] -= 1

        if p1[1] >= 3:
            p1[0] += 1
            p1[1] = p1[1] % 3
            rankup = True
        
        if p2[1] <= -3:
            p2[0] -= 1
            p2[1] = p2[1] % 3
            rankdown = True
        
        return rankup, rankdown

    async def player_autocomplete(self, ctx: discord.AutocompleteContext):
        res = self.database_cur.execute(f"SELECT player_name FROM players")
        name_list=res.fetchall()
        names = set([name[0] for name in name_list])
        return [name for name in names if (name.lower()).startswith(ctx.value.lower())]

    @discord.commands.slash_command(description="help msg")
    async def help(self, ctx : discord.ApplicationContext):
        em = discord.Embed(
            title="Help",
            description="list of all commands",
            color=discord.Color.blurple())
        em.set_thumbnail(
            url=self.bot.user.avatar.url)

        for slash_command in self.walk_commands():
            em.add_field(name=slash_command.name, 
                        value=slash_command.description if slash_command.description else slash_command.name, 
                        inline=False) 
                        # fallbacks to the command name incase command description is not defined

        await ctx.send_response(embed=em)
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
        role_list = []
        role_list.append(discord.utils.get(ctx.guild.roles, name=char1))
        if char2:
            line[2] = char2
            role_list.append(discord.utils.get(ctx.guild.roles, name=char2))
            insert_new_player(tuple(line),self.database_cur)
        if char3:
            line[2] = char3
            role_list.append(discord.utils.get(ctx.guild.roles, name=char3))
            insert_new_player(tuple(line),self.database_cur)
        print(f"Adding to db {player_name} {char1} {char2} {char3}")
        self.database_con.commit()

        print(f"Adding Character and Dan roles to user")
        role_list.append(discord.utils.get(ctx.guild.roles, name="Dan 1"))
        await ctx.author.add_roles(*role_list)

        await ctx.respond(f"""You are now registered as {player_name} with the following character/s {char1} {char2} {char3}\nif you wish to add more characters you can register multiple times!\n\nWelcome to the Danielsen!""")

    @discord.commands.slash_command(description="unregister to the Danisen database!")
    async def unregister(self, ctx : discord.ApplicationContext, 
                    char1 : discord.Option(str, choices=characters)):
        res = self.database_cur.execute(f"SELECT * FROM players WHERE discord_id={ctx.author.id} AND character='{char1}'")
        daniel = res.fetchone()

        print(f"Removing {ctx.author.name} {ctx.author.id} {char1} from db")
        self.database_cur.execute(f"DELETE FROM players WHERE discord_id={ctx.author.id} AND character='{char1}'")
        self.database_con.commit()

        role_list = []
        role_list.append(discord.utils.get(ctx.guild.roles, name=char1))
        print(f"Removing role {char1} from member")

        print(f'Checking if dan should be removed as well')
        res = self.database_cur.execute(f"SELECT * FROM players WHERE discord_id={ctx.author.id} AND dan={daniel['dan']}")
        remaining_daniel = res.fetchone()
        if not remaining_daniel:
            print(f'Dan role {daniel['dan']} will be removed')
            role_list.append(discord.utils.get(ctx.guild.roles, name=f"Dan {daniel['dan']}"))

        await ctx.author.remove_roles(*role_list)

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
            await ctx.respond(f"""{data['player_name']}'s rank for {char} is {data['dan']} dan {data['points']} points""")
        else:
            await ctx.respond(f"""{member.name} is not registered as {char} so you have no rank...""")

    #joins the matchmaking queue
    @discord.commands.slash_command(description="queue up for danisen games")
    async def join_queue(self, ctx : discord.ApplicationContext,
                    char : discord.Option(str, choices=characters)):
        await ctx.defer()
        if ctx.author.id not in self.in_queue.keys():
            print(f"added {ctx.author.name} to in_queue dict")
            self.in_queue[ctx.author.id] = True
        elif self.in_queue[ctx.author.id]:
            await ctx.respond(f"You are already in the queue")
            return

        res = self.database_cur.execute(f"SELECT * FROM players WHERE discord_id={ctx.author.id} AND character='{char}'")
        daniel = res.fetchone()
        if daniel == None:
            await ctx.respond(f"You are not registered with that character")
            return
        dan = daniel['dan']
        await self.daniel_queues[dan].put(daniel)
        await self.matchmaking_queue.put(daniel)
        await ctx.respond(f"You've been added to the matchmaking queue with {char}")

        #matchmake
        if (self.cur_active_matches != self.max_active_matches and
            self.matchmaking_queue.qsize() >= 2):
            print("matchmake function called")
            await self.matchmake(ctx.interaction)

    async def matchmake(self, ctx : discord.Interaction):
        while (self.cur_active_matches != self.max_active_matches and
                self.matchmaking_queue.qsize() >= 2):
            daniel1 = await self.matchmaking_queue.get()
            self.in_queue[ctx.user.id] = False

            if self.dead_daniels[daniel1['dan']] != 0:
                self.dead_daniels[daniel1['dan']] -= 1
                continue

            same_daniel = await self.daniel_queues[daniel1['dan']].get()
            #sanity check that this is also the latest daniel in the respective dan queue
            if daniel1 != same_daniel:
                print(f"Somethings gone very wrong... daniel queues are not synchronized {daniel1=} {same_daniel=}")
                return
            
            #iterate through daniel queues to find suitable opponent
            #will search through queues for an opponent closest in dan prioritizing higher dan
            #x, x+1, x-1, x+2, x-2 etc.
            #e.g. for a dan 3 player we will search the queues as follows
            #3, 4, 2, 5, 1, 6, 7
            #(defaults to ascending order or descending order once out of dans lower or higher resp.)

            #creating daniel iterator (the search pattern defined above)
            check_dan = [daniel1['dan']]
            for dan_offset in range(1, max(self.total_dans-check_dan[0], check_dan[0]-1)):
                cur_dan = check_dan[0] + dan_offset
                if  1 <= cur_dan <= 7:
                    check_dan.append(cur_dan)
                cur_dan = check_dan[0] - dan_offset
                if  1 <= cur_dan <= 7:
                    check_dan.append(cur_dan)
            
            print(f"dan queues to check {check_dan}")
            for dan in check_dan:
                if not self.daniel_queues[dan].empty():
                    daniel2 = await self.daniel_queues[dan].get()
                    self.in_queue[daniel2['discord_id']] = False

                    #this is so we clean up the main queue later for players that have already been matched
                    self.dead_daniels[daniel2['dan']] += 1
                    print(f"match made between {daniel1['player_name']} and {daniel2['player_name']}")
                    await self.create_match_interaction(ctx, daniel1, daniel2)
                    break

    async def create_match_interaction(self, ctx : discord.Interaction,
                                       daniel1, daniel2):
        self.cur_active_matches += 1
        view = MatchView(self, daniel1, daniel2)
        id1 = f'<@{daniel1['discord_id']}>'
        id2 = f'<@{daniel2['discord_id']}>'
        await ctx.respond(id1 +" vs " +id2 +"\n Note only players in the match can report it!",view=view)

    #report match score
    async def report_match(self, interaction: discord.Interaction, player1, player2, winner):
        p1 = [player1['dan'], player1['points']]
        p2 = [player2['dan'], player2['points']]
        if (winner == "player1") :
            self.score_update(p1,p2)
            winner = player1['player_name']
            loser = player2['player_name']
        else:
            self.score_update(p2,p1)
            winner = player2['player_name']
            loser = player1['player_name']
        res = self.database_cur.execute(f"UPDATE players SET dan = {p1[0]}, points = {p1[1]} WHERE player_name='{player1['player_name']}' AND character='{player1['character']}'")
        res = self.database_cur.execute(f"UPDATE players SET dan = {p2[0]}, points = {p2[1]} WHERE player_name='{player2['player_name']}' AND character='{player2['character']}'")
        self.database_con.commit()
        await interaction.respond(f"Match has been reported as {winner}'s victory over {loser}\n{player1['player_name']}'s {player1['character']} rank is now {p1[0]} dan {p1[1]} points\n{player2['player_name']}'s {player2['character']} rank is now {p2[0]} dan {p2[1]} points")


    @discord.commands.slash_command(description="See players in a specific dan")
    async def dan(self, ctx : discord.ApplicationContext,
                  dan : discord.Option(int, min_value=1, max_value=total_dans)):
        res = self.database_cur.execute(f"SELECT * FROM players WHERE dan={dan}")
        daniels = res.fetchall()
        page_list = []
        em = discord.Embed(title=f"Dan {dan}",colour=self.dan_colours[dan-1])
        page_list.append(em)
        page_size = 0
        for daniel in daniels:
            page_size += 1
            page_list[-1].add_field(name=f"{daniel['player_name']} {daniel['character']}", value=f"Dan : {daniel['dan']} Points: {daniel['points']}")
            if page_size == 10:
                em = discord.Embed(title=f"Dan {dan}",colour=self.dan_colours[dan-1])
                page_list.append(em)
                page_size = 0
        paginator = pages.Paginator(pages=page_list)
        await paginator.respond(ctx.interaction, ephemeral=False)
    
    @discord.commands.slash_command(description="UPDATE MAX MATCHES FOR Q")
    @discord.commands.default_permissions(manage_messages=True)
    async def update_max_matches(self, ctx : discord.ApplicationContext,
                                 max : discord.Option(int, min_value=1)):
        self.max_active_matches = max
        await ctx.respond(f"Max matches updated to {max}")

