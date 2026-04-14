import discord
from discord.ext import commands
from discord import app_commands


class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="📊 General", value="general"),
            discord.SelectOption(label="💰 Economy", value="economy"),
            discord.SelectOption(label="⬆️ Leveling", value="leveling"),
            discord.SelectOption(label="🎫 Tickets", value="tickets"),
            discord.SelectOption(label="🎉 Giveaways", value="giveaways"),
            discord.SelectOption(label="🔨 Moderation", value="moderation"),
            discord.SelectOption(label="🛡 Security / Anti-Nuke", value="security"),
            discord.SelectOption(label="📨 Invites & Logs", value="invites"),
            discord.SelectOption(label="🗳 Polls", value="polls"),
            discord.SelectOption(label="👋 Greet System", value="greet"),
        ]

        super().__init__(
            placeholder="Select a command category…",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]

        embeds = {
            "general": (
                "📊 General Commands",
                "**Slash**\n"
                "`/help` `/ping` `/info`\n"
                "`/serverinfo` `/membercount`\n\n"
                "**Prefix**\n"
                "`!ping` `!info`"
            ),

            "economy": (
                "💰 Economy Commands",
                "`bn!cash` `bn!daily`\n"
                "`bn!battle` `bn!fish`\n"
                "`bn!shop` `bn!buy <item>`\n"
                "`bn!inventory` `bn!profile`\n"
                "`bn!top`"
            ),

            "leveling": (
                "⬆️ Leveling Commands",
                "`/rank`\n"
                "`/leaderboard`\n\n"
                "💬 Chat to earn XP automatically"
            ),

            "tickets": (
                "🎫 Ticket System",
                "`/ticket setup`\n"
                "`/ticket close`\n"
                "`/ticket add <user>`\n"
                "`/ticket remove <user>`\n\n"
                "**Ticket Types**\n"
                "• Support\n"
                "• Claim Rewards\n"
                "• Purchase\n"
                "• Partnership"
            ),

            "giveaways": (
                "🎉 Giveaway Commands",
                "`/giveaway duration:30d winners:1 prize:item`\n"
                "`/reroll message_id`\n"
                "`/end message_id`\n\n"
                "⏱ Supports long durations (days / weeks)"
            ),

            "moderation": (
                "🔨 Moderation Commands",
                "`/kick` `/ban` `/unban`\n"
                "`/mute` `/unmute`\n"
                "`/timeout` `/untimeout`\n"
                "`/purge` `/slowmode`\n\n"
                "**Logs**\n"
                "`/moderation-logger type:enable channel:#logs`\n"
                "`/moderation-logger type:disable`"
            ),

            "security": (
                "🛡 Security / Anti-Nuke",
                "**Anti-Nuke Protections**\n"
                "• Role Create / Delete / Update\n"
                "• Channel Create / Delete / Update\n"
                "• Ban / Kick / Bot Add\n"
                "• Webhook Abuse\n"
                "• Emoji Create / Delete / Update\n"
                "• Member Role Update\n\n"
                "**Whitelist**\n"
                "`/whitelist add <user>`\n"
                "`/whitelist remove <user>`"
            ),

            "invites": (
                "📨 Invite & Join Logs",
                "`/invites`\n"
                "`/invited <user>`\n"
                "`/invitetop`\n\n"
                "`/setup-invite-logging channel:#logs`\n\n"
                "Tracks joins, leaves & OAuth joins"
            ),

            "polls": (
                "🗳 Poll Commands",
                "`/poll question option1 option2 ... option11`\n\n"
                "🔢 Auto emoji reactions (1️⃣ – 🔟)\n"
                "Matches number of options exactly"
            ),

            "greet": (
                "👋 Greet System",
                "`/greet setup`\n"
                "`/greet edit`\n"
                "`/greet test`\n\n"
                "Custom join messages with mentions"
            ),
        }

        title, desc = embeds[category]
        embed = discord.Embed(
            title=title,
            description=desc,
            color=discord.Color.blurple()
        )

        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelpSelect())


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------- SLASH --------
    @app_commands.command(name="help", description="Show help menu")
    async def help_slash(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 Bynex Help",
            description="Use the dropdown below to view all commands.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(
            embed=embed,
            view=HelpView(),
            ephemeral=False
        )

    # -------- PREFIX --------
    @commands.command()
    async def help(self, ctx):
        embed = discord.Embed(
            title="🤖 Bynex Help",
            description="Use the dropdown below to view all commands.",
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed, view=HelpView())


async def setup(bot):
    await bot.add_cog(Help(bot))