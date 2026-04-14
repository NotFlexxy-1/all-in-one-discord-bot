import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

DB = "data.db"


class ModerationLogger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect(DB) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS moderation_log (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
            """)
            await db.commit()

    # =========================
    # UTIL
    # =========================

    async def get_log_channel(self, guild: discord.Guild):
        async with aiosqlite.connect(DB) as db:
            async with db.execute(
                "SELECT channel_id FROM moderation_log WHERE guild_id = ?",
                (guild.id,)
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return None
        return guild.get_channel(row[0])

    async def send_log(self, guild, embed):
        channel = await self.get_log_channel(guild)
        if channel:
            await channel.send(embed=embed)

    async def audit_user(self, guild, action, target_id):
        async for entry in guild.audit_logs(limit=1, action=action):
            if entry.target.id == target_id:
                return entry.user, entry.reason
        return None, None

    # =========================
    # EVENTS
    # =========================

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        moderator, reason = await self.audit_user(guild, discord.AuditLogAction.ban, user.id)

        embed = discord.Embed(
            title="🔨 Member Banned",
            color=discord.Color.red()
        )
        embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
        embed.add_field(name="Moderator", value=moderator or "Unknown", inline=False)
        embed.add_field(name="Reason", value=reason or "No reason", inline=False)

        await self.send_log(guild, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        moderator, reason = await self.audit_user(guild, discord.AuditLogAction.unban, user.id)

        embed = discord.Embed(
            title="♻️ Member Unbanned",
            color=discord.Color.green()
        )
        embed.add_field(name="User", value=f"{user} ({user.id})", inline=False)
        embed.add_field(name="Moderator", value=moderator or "Unknown", inline=False)
        embed.add_field(name="Reason", value=reason or "No reason", inline=False)

        await self.send_log(guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        moderator, reason = await self.audit_user(guild, discord.AuditLogAction.kick, member.id)
        if not moderator:
            return

        embed = discord.Embed(
            title="👢 Member Kicked",
            color=discord.Color.orange()
        )
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Moderator", value=moderator, inline=False)
        embed.add_field(name="Reason", value=reason or "No reason", inline=False)

        await self.send_log(guild, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        guild = after.guild

        # TIMEOUT
        if before.timed_out_until != after.timed_out_until:
            action = "⏳ Timeout Added" if after.timed_out_until else "⌛ Timeout Removed"
            color = discord.Color.orange() if after.timed_out_until else discord.Color.green()

            moderator, reason = await self.audit_user(
                guild,
                discord.AuditLogAction.member_update,
                after.id
            )

            embed = discord.Embed(title=action, color=color)
            embed.add_field(name="User", value=f"{after} ({after.id})", inline=False)
            embed.add_field(name="Moderator", value=moderator or "Unknown", inline=False)
            embed.add_field(name="Reason", value=reason or "No reason", inline=False)

            await self.send_log(guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        pass  # mute role logging handled via member_update

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild or message.author.bot:
            return

        moderator, _ = await self.audit_user(
            message.guild,
            discord.AuditLogAction.message_delete,
            message.author.id
        )
        if not moderator:
            return

        embed = discord.Embed(
            title="🧹 Message Deleted",
            color=discord.Color.blurple()
        )
        embed.add_field(name="User", value=message.author, inline=False)
        embed.add_field(name="Moderator", value=moderator, inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)

        await self.send_log(message.guild, embed)

    # =========================
    # SLASH COMMAND
    # =========================

    @app_commands.command(name="moderation-logger", description="Enable or disable moderation logs")
    @app_commands.describe(
        type="enable or disable",
        channel="Log channel (required if enabling)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def moderation_logger(
        self,
        interaction: discord.Interaction,
        type: str,
        channel: discord.TextChannel | None = None
    ):
        type = type.lower()

        async with aiosqlite.connect(DB) as db:
            if type == "enable":
                if not channel:
                    await interaction.response.send_message(
                        "❌ Channel required when enabling",
                        ephemeral=True
                    )
                    return
                await db.execute(
                    "INSERT OR REPLACE INTO moderation_log VALUES (?, ?)",
                    (interaction.guild.id, channel.id)
                )
                await interaction.response.send_message(
                    f"✅ Moderation logs enabled in {channel.mention}",
                    ephemeral=True
                )

            elif type == "disable":
                await db.execute(
                    "DELETE FROM moderation_log WHERE guild_id = ?",
                    (interaction.guild.id,)
                )
                await interaction.response.send_message(
                    "❌ Moderation logs disabled",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Type must be enable or disable",
                    ephemeral=True
                )

            await db.commit()


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationLogger(bot))
