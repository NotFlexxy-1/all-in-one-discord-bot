import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import re
import time
from collections import defaultdict

DB = "data.db"
LINK_REGEX = re.compile(r"(https?://|www\.)", re.I)

def get_db():
    return sqlite3.connect(DB)

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_cache = defaultdict(list)

        with get_db() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS security (
                    guild_id INTEGER PRIMARY KEY,
                    anti_link INTEGER DEFAULT 0,
                    anti_spam INTEGER DEFAULT 0,
                    max_msgs INTEGER DEFAULT 5,
                    seconds INTEGER DEFAULT 5
                )
            """)

    # ---------------- EVENTS ----------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        with get_db() as db:
            cur = db.execute(
                "SELECT anti_link, anti_spam, max_msgs, seconds FROM security WHERE guild_id=?",
                (message.guild.id,)
            )
            row = cur.fetchone()

        if not row:
            await self.bot.process_commands(message)
            return

        anti_link, anti_spam, max_msgs, seconds = row

        # ---- ANTI LINK ----
        if anti_link and LINK_REGEX.search(message.content):
            if not message.author.guild_permissions.manage_messages:
                await message.delete()
                await message.channel.send(
                    f"🚫 {message.author.mention} links are not allowed.",
                    delete_after=5
                )
                return

        # ---- ANTI SPAM ----
        if anti_spam:
            now = time.time()
            cache = self.message_cache[message.author.id]
            cache.append(now)

            self.message_cache[message.author.id] = [
                t for t in cache if now - t <= seconds
            ]

            if len(self.message_cache[message.author.id]) >= max_msgs:
                try:
                    await message.delete()
                    await message.channel.send(
                        f"⚠️ {message.author.mention} slow down (spam detected).",
                        delete_after=5
                    )
                except discord.Forbidden:
                    pass
                return

        await self.bot.process_commands(message)

    # ---------------- SLASH COMMANDS ----------------
    @app_commands.command(name="antilink", description="Enable or disable anti-link")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def antilink_slash(self, interaction: discord.Interaction, enabled: bool):
        with get_db() as db:
            db.execute(
                "INSERT OR IGNORE INTO security (guild_id) VALUES (?)",
                (interaction.guild.id,)
            )
            db.execute(
                "UPDATE security SET anti_link=? WHERE guild_id=?",
                (int(enabled), interaction.guild.id)
            )

        await interaction.response.send_message(
            f"✅ Anti-link {'enabled' if enabled else 'disabled'}",
            ephemeral=True
        )

    @app_commands.command(name="antispam", description="Enable or configure anti-spam")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def antispam_slash(
        self,
        interaction: discord.Interaction,
        enabled: bool,
        max_messages: int = 5,
        seconds: int = 5
    ):
        with get_db() as db:
            db.execute(
                "INSERT OR REPLACE INTO security VALUES (?, ?, ?, ?, ?)",
                (interaction.guild.id, 0, int(enabled), max_messages, seconds)
            )

        await interaction.response.send_message(
            f"✅ Anti-spam {'enabled' if enabled else 'disabled'} "
            f"({max_messages} msgs / {seconds}s)",
            ephemeral=True
        )

    # ---------------- PREFIX COMMANDS ----------------
    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def antilink(self, ctx, enabled: bool):
        with get_db() as db:
            db.execute(
                "INSERT OR IGNORE INTO security (guild_id) VALUES (?)",
                (ctx.guild.id,)
            )
            db.execute(
                "UPDATE security SET anti_link=? WHERE guild_id=?",
                (int(enabled), ctx.guild.id)
            )

        await ctx.send(f"✅ Anti-link {'enabled' if enabled else 'disabled'}")

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def antispam(self, ctx, enabled: bool, max_messages: int = 5, seconds: int = 5):
        with get_db() as db:
            db.execute(
                "INSERT OR REPLACE INTO security VALUES (?, ?, ?, ?, ?)",
                (ctx.guild.id, 0, int(enabled), max_messages, seconds)
            )

        await ctx.send(
            f"✅ Anti-spam {'enabled' if enabled else 'disabled'} "
            f"({max_messages} msgs / {seconds}s)"
        )

async def setup(bot):
    await bot.add_cog(Security(bot))
