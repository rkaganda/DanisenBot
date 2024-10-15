import discord
class MatchSelect(discord.ui.Select):
    def __init__(self, bot, p1, p2):
        self.p1 = p1
        self.p2 = p2
        self.bot = bot
        options = [
            discord.SelectOption(
                label=f"{p1["player_name"]} {p1["character"]}",
                description=f"{p1["player_name"]} victory!"
            ),
            discord.SelectOption(
                label=f"{p2["player_name"]} {p2["character"]}",
                description=f"{p2["player_name"]} victory!"
            ),
            discord.SelectOption(
                label="Cancel",
                description="Cancel the match"
            )
        ]
    
        super().__init__(
            placeholder = "Report match winner",
            min_values = 1,
            max_values = 1,
            options = options
        )

    async def callback(self, interaction: discord.Interaction):
        valid_ids = [self.p1['discord_id'], self.p2['discord_id']]
        if interaction.user.id not in valid_ids:
            return
        self.disabled=True
        self.view.disable_all_items()
        self.view.stop()
        print("Match has been reported")
        self.bot.cur_active_matches -= 1
        print(f"cur_active_matches reduced {self.bot.cur_active_matches}")
        if self.values[0] == "Cancel":
            await interaction.response.send_message(f"Match has been cancelled, please queue up again if you wish to play")
        elif self.values[0] == f"{self.p1["player_name"]} {self.p1["character"]}":
            await self.bot.report_match_queue(interaction, self.p1,self.p2, "player1")
        else:
            await self.bot.report_match_queue(interaction, self.p1,self.p2, "player2")
        await self.bot.matchmake(interaction)
        await interaction.message.delete()

class MatchView(discord.ui.View):
    def __init__(self, bot, p1, p2):
        super().__init__(timeout=None)
        self.add_item(MatchSelect(bot, p1, p2))
