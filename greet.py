import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

DB = "data.db"


class Greet(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =========================
    # DATABASE INIT
    # =========================
    async def cog_load(self):
        async with aiosqlite.connect(DB) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS greet (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                message TEXT NOT NULL
            )
            """)
            await db.commit()

    # =========================
    # INTERNAL HELPERS
    # =========================
    async def get_greet(self, guild_id: int):
        async with aiosqlite.connect(DB) as db:
            async with db.execute(
                "SELECT channel_id, message FROM greet WHERE guild_id = ?",
                (guild_id,)
            ) as cur:
                return await cur.fetchone()

    # =========================
    # EVENTS
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = await self.get_greet(member.guild.id)
        if not data:
            return

        channel_id, message = data
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        text = (
            message
            .replace("{user}", member.mention)
            .replace("{server}", member.guild.name)
            .replace("{membercount}", str(member.guild.member_count))
        )

        await channel.send(text)

    # =========================
    # SLASH GROUP
    # =========================
    greet = app_commands.Group(
        name="greet",
        description="Welcome / greet system configuration"
    )

    # =========================
    # /greet setup
    # =========================
    @greet.command(
        name="setup",
        description="Setup greet system with default welcome message"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def greet_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        await interaction.response.defer(ephemeral=True)

        default_message = (
            "👋 Welcome {user} to **{server}**!\n"
            "You are our **{membercount}th** member 🎉"
        )

        async with aiosqlite.connect(DB) as db:
            await db.execute("""
            INSERT OR REPLACE INTO greet (guild_id, channel_id, message)
            VALUES (?, ?, ?)
            """, (interaction.guild.id, channel.id, default_message))
            await db.commit()

        await interaction.followup.send(
            f"✅ Greet system enabled in {channel.mention}",
            ephemeral=True
        )

    # =========================
    # /greet edit
    # =========================
    @greet.command(
        name="edit",
        description="Edit greet message"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def greet_edit(
        self,
        interaction: discord.Interaction,
        message: str
    ):
        await interaction.response.defer(ephemeral=True)

        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT channel_id FROM greet WHERE guild_id = ?",
                (interaction.guild.id,)
            )
            row = await cur.fetchone()

            if not row:
                await interaction.followup.send(
                    "❌ Greet system is not set up.",
                    ephemeral=True
                )
                return

            await db.execute(
                "UPDATE greet SET message = ? WHERE guild_id = ?",
                (message, interaction.guild.id)
            )
            await db.commit()

        await interaction.followup.send(
            "✅ Greet message updated.\n"
            "**Variables:** `{user}` `{server}` `{membercount}`",
            ephemeral=True
        )

    # =========================
    # /greet test
    # =========================
    @greet.command(
        name="test",
        description="Test greet message"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def greet_test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        data = await self.get_greet(interaction.guild.id)
        if not data:
            await interaction.followup.send(
                "❌ Greet system not enabled.",
                ephemeral=True
            )
            return

        channel_id, message = data
        channel = interaction.guild.get_channel(channel_id)

        if not channel:
            await interaction.followup.send(
                "❌ Greet channel missing.",
                ephemeral=True
            )
            return

        preview = (
            message
            .replace("{user}", interaction.user.mention)
            .replace("{server}", interaction.guild.name)
            .replace("{membercount}", str(interaction.guild.member_count))
        )

        await channel.send(preview)
        await interaction.followup.send(
            "✅ Greet message sent.",
            ephemeral=True
        )

    # =========================
    # /greet disable
    # =========================
    @greet.command(
        name="disable",
        description="Disable greet system"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def greet_disable(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "DELETE FROM greet WHERE guild_id = ?",
                (interaction.guild.id,)
            )
            await db.commit()

        await interaction.followup.send(
            "🛑 Greet system disabled.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Greet(bot))
