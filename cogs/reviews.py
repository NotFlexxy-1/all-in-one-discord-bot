import json
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

CONFIG_FILE = "guild_feedback_config.json"


# ---------------- CONFIG HELPERS ----------------
def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


def get_guild_config(guild_id: int):
    config = load_config()
    return config.get(str(guild_id), {})


def set_guild_config(guild_id: int, key: str, value):
    config = load_config()
    guild_id = str(guild_id)

    if guild_id not in config:
        config[guild_id] = {}

    config[guild_id][key] = value
    save_config(config)


# ---------------- REVIEW MODAL ----------------
class ReviewModal(discord.ui.Modal, title="⭐ Submit Your Review"):
    rating = discord.ui.TextInput(
        label="Service Rating (1–5)",
        placeholder="Example: 5",
        max_length=1,
        required=True
    )

    review = discord.ui.TextInput(
        label="Your Review",
        placeholder="Share your experience...",
        style=discord.TextStyle.paragraph,
        max_length=600,
        required=True
    )

    image_url = discord.ui.TextInput(
        label="Optional Image URL",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message(
                "❌ Reviews can only be submitted inside a server.",
                ephemeral=True
            )

        if not self.rating.value.isdigit() or not (1 <= int(self.rating.value) <= 5):
            return await interaction.response.send_message(
                "❌ Rating must be between **1 and 5**.",
                ephemeral=True
            )

        guild_config = get_guild_config(interaction.guild.id)
        channel_id = guild_config.get("feedback_channel")
        hostname = guild_config.get("hostname", "Unnamed Host")

        if not channel_id:
            return await interaction.response.send_message(
                "⚠️ Feedback channel is not set for this server.",
                ephemeral=True
            )

        channel = interaction.client.get_channel(channel_id)
        if not channel:
            return await interaction.response.send_message(
                "❌ Feedback channel not found.",
                ephemeral=True
            )

        stars = "⭐" * int(self.rating.value)

        embed = discord.Embed(
            title=f"{hostname} Reviews",
            description=f"📢 **New Service Review**\n\n{self.review.value}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="⭐ Service Rating",
            value=f"{stars} ({self.rating.value}/5)",
            inline=False
        )

        embed.add_field(
            name="👤 Reviewed by",
            value=interaction.user.mention,
            inline=False
        )

        embed.set_footer(text=f"{hostname} • Premium Hosting")

        if self.image_url.value:
            embed.set_thumbnail(url=self.image_url.value)

        await channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ **Your review has been submitted successfully!**",
            ephemeral=True
        )


# ---------------- COG ----------------
class Reviews(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="review",
        description="Submit a service review"
    )
    async def review(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ReviewModal())

    @app_commands.command(
        name="set-feedback-channel",
        description="Set the review output channel for this server"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_feedback_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        if not interaction.guild:
            return await interaction.response.send_message(
                "❌ This command must be used in a server.",
                ephemeral=True
            )

        set_guild_config(interaction.guild.id, "feedback_channel", channel.id)

        embed = discord.Embed(
            description=f"✅ **Feedback channel set to** {channel.mention}",
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="set-hostname",
        description="Set the hosting name shown in reviews"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_hostname(
        self,
        interaction: discord.Interaction,
        name: str
    ):
        if not interaction.guild:
            return await interaction.response.send_message(
                "❌ This command must be used in a server.",
                ephemeral=True
            )

        set_guild_config(interaction.guild.id, "hostname", name)

        embed = discord.Embed(
            description=f"✅ **Hostname set to** `{name}`",
            color=discord.Color.blue()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Reviews(bot))
