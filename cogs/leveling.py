import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import random
import time

DB = "data.db"

XP_MIN = 15
XP_MAX = 25
XP_COOLDOWN = 60  # seconds


class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldowns = {}

    # =========================
    # DATABASE INIT
    # =========================
    async def cog_load(self):
        async with aiosqlite.connect(DB) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                guild_id INTEGER,
                user_id INTEGER,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                last_xp INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
            """)
            await db.execute("""
            CREATE TABLE IF NOT EXISTS level_settings (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                enabled INTEGER DEFAULT 1
            )
            """)
            await db.commit()

    # =========================
    # XP CALCULATION
    # =========================
    def xp_for_next_level(self, level: int) -> int:
        return 5 * (level ** 2) + 50 * level + 100

    # =========================
    # MESSAGE LISTENER
    # =========================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (
            message.author.bot
            or not message.guild
            or len(message.content) < 5
        ):
            return

        now = int(time.time())
        key = (message.guild.id, message.author.id)

        if key in self.cooldowns and now - self.cooldowns[key] < XP_COOLDOWN:
            return

        self.cooldowns[key] = now
        xp_gain = random.randint(XP_MIN, XP_MAX)

        async with aiosqlite.connect(DB) as db:
            await db.execute("""
            INSERT OR IGNORE INTO levels (guild_id, user_id, xp, level, last_xp)
            VALUES (?, ?, 0, 0, 0)
            """, (message.guild.id, message.author.id))

            cur = await db.execute("""
            SELECT xp, level FROM levels
            WHERE guild_id = ? AND user_id = ?
            """, (message.guild.id, message.author.id))
            xp, level = await cur.fetchone()

            new_xp = xp + xp_gain
            next_level_xp = self.xp_for_next_level(level)
            leveled_up = False

            while new_xp >= next_level_xp:
                new_xp -= next_level_xp
                level += 1
                next_level_xp = self.xp_for_next_level(level)
                leveled_up = True

            await db.execute("""
            UPDATE levels
            SET xp = ?, level = ?, last_xp = ?
            WHERE guild_id = ? AND user_id = ?
            """, (new_xp, level, now, message.guild.id, message.author.id))

            await db.commit()

        if leveled_up:
            await self.send_level_up(message.author, message.guild, level)

    # =========================
    # LEVEL UP MESSAGE
    # =========================
    async def send_level_up(self, member, guild, level):
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT channel_id FROM level_settings WHERE guild_id = ?",
                (guild.id,)
            )
            row = await cur.fetchone()

        channel = guild.get_channel(row[0]) if row and row[0] else guild.system_channel
        if not channel:
            return

        embed = discord.Embed(
            title="✨ Level Up!",
            description=f"{member.mention} reached **Level {level}** 🎉",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        await channel.send(embed=embed)

    # =========================
    # SLASH COMMANDS
    # =========================
    leveling = app_commands.Group(
        name="leveling",
        description="Leveling system commands"
    )

    @leveling.command(
        name="rank",
        description="Check your rank"
    )
    async def rank(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await interaction.response.defer()

        member = member or interaction.user

        async with aiosqlite.connect(DB) as db:
            cur = await db.execute("""
            SELECT xp, level FROM levels
            WHERE guild_id = ? AND user_id = ?
            """, (interaction.guild.id, member.id))
            row = await cur.fetchone()

        if not row:
            await interaction.followup.send("❌ No data found.")
            return

        xp, level = row
        next_xp = self.xp_for_next_level(level)

        embed = discord.Embed(
            title=f"📊 Rank — {member}",
            color=discord.Color.green()
        )
        embed.add_field(name="Level", value=level, inline=True)
        embed.add_field(name="XP", value=f"{xp}/{next_xp}", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)

        await interaction.followup.send(embed=embed)

    @leveling.command(
        name="leaderboard",
        description="Top 10 users"
    )
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()

        async with aiosqlite.connect(DB) as db:
            cur = await db.execute("""
            SELECT user_id, level, xp FROM levels
            WHERE guild_id = ?
            ORDER BY level DESC, xp DESC
            LIMIT 10
            """, (interaction.guild.id,))
            rows = await cur.fetchall()

        if not rows:
            await interaction.followup.send("❌ No data yet.")
            return

        desc = ""
        for i, (uid, lvl, xp) in enumerate(rows, start=1):
            user = interaction.guild.get_member(uid)
            name = user.mention if user else f"<@{uid}>"
            desc += f"**#{i}** {name} — Level {lvl} ({xp} XP)\n"

        embed = discord.Embed(
            title="🏆 Leaderboard",
            description=desc,
            color=discord.Color.gold()
        )

        await interaction.followup.send(embed=embed)

    @leveling.command(
        name="set-channel",
        description="Set level-up message channel"
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
            INSERT OR REPLACE INTO level_settings (guild_id, channel_id, enabled)
            VALUES (?, ?, 1)
            """, (interaction.guild.id, channel.id))
            await db.commit()

        await interaction.followup.send(
            f"✅ Level-up messages set to {channel.mention}",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))
