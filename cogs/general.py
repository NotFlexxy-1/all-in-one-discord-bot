import discord
from discord import app_commands
from discord.ext import commands
from config import EMBED_COLOR, BOT_NAME

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /ping
    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(
            f"🏓 Pong! `{latency}ms`",
            ephemeral=True
        )

    # /info
    @app_commands.command(name="info", description="Bot information")
    async def info(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"🤖 {BOT_NAME}",
            description="Public multipurpose Discord bot",
            color=EMBED_COLOR
        )
        embed.add_field(name="Servers", value=len(self.bot.guilds))
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms")
        embed.set_footer(text="Legendary bot framework")

        await interaction.response.send_message(embed=embed)

    # /serverinfo
    @app_commands.command(name="serverinfo", description="Show server information")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild

        embed = discord.Embed(
            title=f"🏠 {guild.name}",
            color=EMBED_COLOR
        )
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Owner", value=guild.owner)
        embed.add_field(name="Created", value=guild.created_at.strftime("%d %B %Y"))
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

        await interaction.response.send_message(embed=embed)

    # /membercount
    @app_commands.command(name="membercount", description="Show member count")
    async def membercount(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"👥 Members: **{interaction.guild.member_count}**"
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
