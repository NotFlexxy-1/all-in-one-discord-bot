import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

DB = "data.db"

def get_db():
    return sqlite3.connect(DB)

class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with get_db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS autorole (guild_id INTEGER PRIMARY KEY, role_id INTEGER)"
            )

    # ---------- EVENTS ----------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        with get_db() as db:
            cur = db.execute(
                "SELECT role_id FROM autorole WHERE guild_id = ?",
                (member.guild.id,)
            )
            row = cur.fetchone()

        if not row:
            return

        role = member.guild.get_role(row[0])
        if role:
            try:
                await member.add_roles(role, reason="Auto-role")
            except discord.Forbidden:
                pass

    # ---------- SLASH ----------
    @app_commands.command(name="autorole", description="Set auto-role for new members")
    @app_commands.describe(role="Role to give on join")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def autorole_slash(self, interaction: discord.Interaction, role: discord.Role):
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "❌ I can't assign that role (role hierarchy).",
                ephemeral=True
            )
            return

        with get_db() as db:
            db.execute(
                "INSERT OR REPLACE INTO autorole (guild_id, role_id) VALUES (?, ?)",
                (interaction.guild.id, role.id)
            )

        await interaction.response.send_message(
            f"✅ Auto-role set to **{role.name}**",
            ephemeral=True
        )

    @app_commands.command(name="autorole_remove", description="Disable auto-role")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def autorole_remove_slash(self, interaction: discord.Interaction):
        with get_db() as db:
            db.execute(
                "DELETE FROM autorole WHERE guild_id = ?",
                (interaction.guild.id,)
            )

        await interaction.response.send_message(
            "✅ Auto-role disabled",
            ephemeral=True
        )

    # ---------- PREFIX ----------
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def autorole(self, ctx, role: discord.Role):
        if role >= ctx.guild.me.top_role:
            await ctx.send("❌ I can't assign that role (role hierarchy).")
            return

        with get_db() as db:
            db.execute(
                "INSERT OR REPLACE INTO autorole (guild_id, role_id) VALUES (?, ?)",
                (ctx.guild.id, role.id)
            )

        await ctx.send(f"✅ Auto-role set to **{role.name}**")

    @commands.command(name="autorole_remove")
    @commands.has_permissions(manage_roles=True)
    async def autorole_remove(self, ctx):
        with get_db() as db:
            db.execute(
                "DELETE FROM autorole WHERE guild_id = ?",
                (ctx.guild.id,)
            )

        await ctx.send("✅ Auto-role disabled")

async def setup(bot):
    await bot.add_cog(AutoRole(bot))
