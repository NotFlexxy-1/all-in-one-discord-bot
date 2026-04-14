import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiosqlite
import asyncio
import time
import random
import re

DB_PATH = "data.db"
EMOJI = "🎉"


def parse_duration(duration: str) -> int:
    """
    Converts 30d / 12h / 10m / 30s → seconds
    """
    match = re.fullmatch(r"(\d+)([smhd])", duration.lower())
    if not match:
        return 0

    value, unit = match.groups()
    value = int(value)

    return {
        "s": value,
        "m": value * 60,
        "h": value * 3600,
        "d": value * 86400,
    }[unit]


class Giveaways(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_giveaways.start()

    async def cog_load(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                message_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                prize TEXT,
                end_time INTEGER,
                winners INTEGER
            )
            """)
            await db.commit()

    def cog_unload(self):
        self.check_giveaways.cancel()

    # ======================
    # SLASH COMMANDS
    # ======================

    @app_commands.command(name="giveaway", description="Start a giveaway")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        duration="Example: 30d, 12h, 45m",
        prize="Giveaway prize",
        winners="Number of winners"
    )
    async def giveaway(
        self,
        interaction: discord.Interaction,
        duration: str,
        prize: str,
        winners: int
    ):
        seconds = parse_duration(duration)
        if seconds <= 0:
            return await interaction.response.send_message(
                "❌ Invalid duration. Use `30d`, `12h`, `10m`, `30s`",
                ephemeral=True
            )

        if winners < 1 or winners > 20:
            return await interaction.response.send_message(
                "❌ Winners must be between 1 and 20",
                ephemeral=True
            )

        end_time = int(time.time()) + seconds

        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=(
                f"🎁 **Prize:** {prize}\n"
                f"🏆 **Winners:** {winners}\n"
                f"⏰ **Ends:** <t:{end_time}:R>\n\n"
                f"React with {EMOJI} to enter!"
            ),
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Hosted by {interaction.user}")

        await interaction.response.send_message("✅ Giveaway started", ephemeral=True)
        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction(EMOJI)

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO giveaways VALUES (?, ?, ?, ?, ?)",
                (msg.id, interaction.channel.id, prize, end_time, winners)
            )
            await db.commit()

    @app_commands.command(name="end", description="End a giveaway early")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def end(self, interaction: discord.Interaction, message_id: str):
        await self.finish_giveaway(int(message_id), forced=True)
        await interaction.response.send_message("🛑 Giveaway ended")

    @app_commands.command(name="reroll", description="Reroll a giveaway")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reroll(self, interaction: discord.Interaction, message_id: str):
        await self.finish_giveaway(int(message_id), reroll=True)
        await interaction.response.send_message("🔁 Giveaway rerolled")

    # ======================
    # BACKGROUND TASK
    # ======================

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        now = int(time.time())

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT message_id FROM giveaways WHERE end_time <= ?",
                (now,)
            ) as cursor:
                rows = await cursor.fetchall()

        for (message_id,) in rows:
            await self.finish_giveaway(message_id)

    @check_giveaways.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # ======================
    # CORE LOGIC
    # ======================

    async def finish_giveaway(self, message_id: int, forced=False, reroll=False):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT channel_id, prize, winners FROM giveaways WHERE message_id = ?",
                (message_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                return

            channel_id, prize, winners = row

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        try:
            msg = await channel.fetch_message(message_id)
        except:
            return

        reaction = discord.utils.get(msg.reactions, emoji=EMOJI)
        if not reaction:
            await channel.send("❌ No entries.")
            return

        users = [u async for u in reaction.users() if not u.bot]

        if len(users) < winners:
            await channel.send("❌ Not enough participants.")
            return

        selected = random.sample(users, winners)
        mentions = ", ".join(u.mention for u in selected)

        embed = discord.Embed(
            title="🎉 GIVEAWAY ENDED 🎉",
            description=(
                f"🎁 **Prize:** {prize}\n"
                f"🏆 **Winners:** {mentions}"
            ),
            color=discord.Color.green()
        )

        await channel.send(embed=embed)

        if not reroll:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "DELETE FROM giveaways WHERE message_id = ?",
                    (message_id,)
                )
                await db.commit()


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaways(bot))
