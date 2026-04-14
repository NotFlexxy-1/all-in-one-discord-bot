import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

DB = "data.db"


class InviteLogger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.invite_cache = {}

    # =========================
    # INIT
    # =========================
    async def cog_load(self):
        async with aiosqlite.connect(DB) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS invite_settings (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
            """)
            await db.execute("""
            CREATE TABLE IF NOT EXISTS invite_joins (
                guild_id INTEGER,
                user_id INTEGER,
                inviter_id INTEGER
            )
            """)
            await db.commit()

        for guild in self.bot.guilds:
            await self.cache_invites(guild)

    async def cache_invites(self, guild: discord.Guild):
        try:
            self.invite_cache[guild.id] = await guild.invites()
        except discord.Forbidden:
            self.invite_cache[guild.id] = []

    # =========================
    # EVENTS
    # =========================
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self.cache_invites(guild)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        await self.cache_invites(invite.guild)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        await self.cache_invites(invite.guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        before = self.invite_cache.get(guild.id, [])
        await self.cache_invites(guild)
        after = self.invite_cache.get(guild.id, [])

        inviter = None

        for old in before:
            for new in after:
                if old.code == new.code and old.uses < new.uses:
                    inviter = new.inviter
                    break

        async with aiosqlite.connect(DB) as db:
            await db.execute("""
            INSERT INTO invite_joins (guild_id, user_id, inviter_id)
            VALUES (?, ?, ?)
            """, (guild.id, member.id, inviter.id if inviter else None))
            await db.commit()

        channel_id = await self.get_log_channel(guild.id)
        if not channel_id:
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title="📨 Member Joined",
            description=(
                f"👤 {member.mention}\n"
                f"📩 Invited by: {inviter.mention if inviter else 'Unknown'}"
            ),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute("""
            SELECT inviter_id FROM invite_joins
            WHERE guild_id = ? AND user_id = ?
            """, (member.guild.id, member.id))
            row = await cur.fetchone()

        inviter = member.guild.get_member(row[0]) if row and row[0] else None

        channel_id = await self.get_log_channel(member.guild.id)
        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title="📤 Member Left",
            description=(
                f"👤 {member}\n"
                f"📩 Invited by: {inviter.mention if inviter else 'Unknown'}"
            ),
            color=discord.Color.red()
        )

        await channel.send(embed=embed)

    # =========================
    # SLASH COMMAND
    # =========================
    invite = app_commands.Group(
        name="invite",
        description="Invite logger settings"
    )

    @invite.command(
        name="set-channel",
        description="Set invite log channel"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        await interaction.response.defer(ephemeral=True)

        async with aiosqlite.connect(DB) as db:
            await db.execute("""
            INSERT OR REPLACE INTO invite_settings (guild_id, channel_id)
            VALUES (?, ?)
            """, (interaction.guild.id, channel.id))
            await db.commit()

        await interaction.followup.send(
            f"✅ Invite logs set to {channel.mention}",
            ephemeral=True
        )

    # =========================
    # HELPERS
    # =========================
    async def get_log_channel(self, guild_id: int):
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT channel_id FROM invite_settings WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cur.fetchone()
            return row[0] if row else None


async def setup(bot: commands.Bot):
    await bot.add_cog(InviteLogger(bot))
