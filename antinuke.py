import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import time
from typing import Literal

DB = "data.db"


class AntiNuke(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldowns = {}

    # =========================
    # DATABASE
    # =========================
    async def cog_load(self):
        async with aiosqlite.connect(DB) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS antinuke_config (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER DEFAULT 0,
                punishment TEXT DEFAULT 'kick',
                log_channel INTEGER
            )
            """)
            await db.execute("""
            CREATE TABLE IF NOT EXISTS antinuke_whitelist (
                guild_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
            """)
            await db.commit()

    # =========================
    # HELPERS
    # =========================
    async def get_config(self, guild_id: int):
        async with aiosqlite.connect(DB) as db:
            async with db.execute(
                "SELECT enabled, punishment, log_channel FROM antinuke_config WHERE guild_id = ?",
                (guild_id,)
            ) as cur:
                return await cur.fetchone()

    async def is_whitelisted(self, guild_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(DB) as db:
            async with db.execute(
                "SELECT 1 FROM antinuke_whitelist WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id)
            ) as cur:
                return await cur.fetchone() is not None

    def ratelimit(self, guild_id: int, user_id: int) -> bool:
        now = time.time()
        key = (guild_id, user_id)
        last = self.cooldowns.get(key, 0)

        if now - last < 3:
            return True

        self.cooldowns[key] = now
        return False

    async def log(self, guild: discord.Guild, message: str):
        config = await self.get_config(guild.id)
        if not config or not config[2]:
            return

        channel = guild.get_channel(config[2])
        if channel:
            await channel.send(message)

    async def punish(self, guild: discord.Guild, member: discord.Member, reason: str):
        if member == guild.owner:
            return

        config = await self.get_config(guild.id)
        if not config:
            return

        try:
            if config[1] == "ban":
                await guild.ban(member, reason=reason)
            else:
                await guild.kick(member, reason=reason)
        except:
            pass

        await self.log(
            guild,
            f"🚨 **ANTI-NUKE TRIGGERED**\n"
            f"User: `{member}`\n"
            f"Action: `{reason}`\n"
            f"Punishment: `{config[1]}`"
        )

    async def get_executor(self, guild, action, target_id):
        async for entry in guild.audit_logs(limit=5, action=action):
            if entry.target and entry.target.id == target_id:
                return entry.user
        return None

    async def antinuke_check(self, guild, action, target_id, reason):
        config = await self.get_config(guild.id)
        if not config or not config[0]:
            return

        executor = await self.get_executor(guild, action, target_id)
        if not executor or not isinstance(executor, discord.Member):
            return

        if await self.is_whitelisted(guild.id, executor.id):
            return

        if self.ratelimit(guild.id, executor.id):
            return

        await self.punish(guild, executor, reason)

    # =========================
    # EVENTS
    # =========================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        await self.antinuke_check(
            channel.guild,
            discord.AuditLogAction.channel_create,
            channel.id,
            "Channel Create"
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await self.antinuke_check(
            channel.guild,
            discord.AuditLogAction.channel_delete,
            channel.id,
            "Channel Delete"
        )

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        await self.antinuke_check(
            role.guild,
            discord.AuditLogAction.role_create,
            role.id,
            "Role Create"
        )

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        await self.antinuke_check(
            role.guild,
            discord.AuditLogAction.role_delete,
            role.id,
            "Role Delete"
        )

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        await self.antinuke_check(
            guild,
            discord.AuditLogAction.ban,
            user.id,
            "Member Ban"
        )

    # =========================
    # SLASH COMMANDS
    # =========================
    antinuke = app_commands.Group(
        name="antinuke",
        description="Anti-nuke protection system"
    )

    @antinuke.command(name="enable")
    async def enable(self, interaction: discord.Interaction):
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "INSERT OR REPLACE INTO antinuke_config (guild_id, enabled) VALUES (?, 1)",
                (interaction.guild.id,)
            )
            await db.commit()

        await interaction.response.send_message("✅ Anti-nuke enabled", ephemeral=True)

    @antinuke.command(name="disable")
    async def disable(self, interaction: discord.Interaction):
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "UPDATE antinuke_config SET enabled = 0 WHERE guild_id = ?",
                (interaction.guild.id,)
            )
            await db.commit()

        await interaction.response.send_message("❌ Anti-nuke disabled", ephemeral=True)

    @antinuke.command(name="punishment")
    async def punishment(
        self,
        interaction: discord.Interaction,
        mode: Literal["kick", "ban"]
    ):
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "UPDATE antinuke_config SET punishment = ? WHERE guild_id = ?",
                (mode, interaction.guild.id)
            )
            await db.commit()

        await interaction.response.send_message(
            f"⚖️ Punishment set to **{mode}**",
            ephemeral=True
        )

    @antinuke.command(name="log-channel")
    async def log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "UPDATE antinuke_config SET log_channel = ? WHERE guild_id = ?",
                (channel.id, interaction.guild.id)
            )
            await db.commit()

        await interaction.response.send_message(
            f"📜 Logs set to {channel.mention}",
            ephemeral=True
        )

    whitelist = app_commands.Group(
        name="whitelist",
        description="Manage antinuke whitelist",
        parent=antinuke
    )

    @whitelist.command(name="add")
    async def whitelist_add(self, interaction: discord.Interaction, member: discord.Member):
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "INSERT OR IGNORE INTO antinuke_whitelist VALUES (?, ?)",
                (interaction.guild.id, member.id)
            )
            await db.commit()

        await interaction.response.send_message(
            f"✅ {member.mention} whitelisted",
            ephemeral=True
        )

    @whitelist.command(name="remove")
    async def whitelist_remove(self, interaction: discord.Interaction, member: discord.Member):
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "DELETE FROM antinuke_whitelist WHERE guild_id = ? AND user_id = ?",
                (interaction.guild.id, member.id)
            )
            await db.commit()

        await interaction.response.send_message(
            f"❌ {member.mention} removed from whitelist",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiNuke(bot))
