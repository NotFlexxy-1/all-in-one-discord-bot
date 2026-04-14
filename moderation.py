import discord
from discord import app_commands
from discord.ext import commands
from config import EMBED_COLOR, DEFAULT_SLOWMODE

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /kick
    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided"
    ):
        await member.kick(reason=reason)
        await interaction.response.send_message(
            f"👢 **{member}** kicked\n📝 Reason: {reason}"
        )

    # /ban
    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided"
    ):
        await member.ban(reason=reason)
        await interaction.response.send_message(
            f"🔨 **{member}** banned\n📝 Reason: {reason}"
        )

    # /unban
    @app_commands.command(name="unban", description="Unban a user by ID")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str
    ):
        user = await self.bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"♻️ **{user}** unbanned")

    # /mute (timeout)
    @app_commands.command(name="mute", description="Timeout a member")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: int,
        reason: str = "No reason provided"
    ):
        await member.timeout(
            discord.utils.utcnow() + discord.timedelta(minutes=minutes),
            reason=reason
        )
        await interaction.response.send_message(
            f"🔇 **{member}** muted for {minutes} minutes"
        )

    # /unmute
    @app_commands.command(name="unmute", description="Remove timeout from a member")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        await member.timeout(None)
        await interaction.response.send_message(f"🔊 **{member}** unmuted")

    # /purge
    @app_commands.command(name="purge", description="Delete messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: int
    ):
        await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(
            f"🧹 Deleted **{amount}** messages",
            ephemeral=True
        )

    # /slowmode
    @app_commands.command(name="slowmode", description="Set slowmode in channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: int = DEFAULT_SLOWMODE
    ):
        await interaction.channel.edit(slowmode_delay=seconds)
        await interaction.response.send_message(
            f"🐢 Slowmode set to **{seconds}s**"
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
