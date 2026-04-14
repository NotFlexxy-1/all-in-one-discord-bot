import discord
from discord import app_commands
from discord.ext import commands
import json
import os

DATA_FILE = "payment_methods.json"

# Emoji mappings — only shown next to the crypto name in the list
CRYPTO_EMOJIS = {
    "LTC": "<:LTC:1469015514666766527>",
    "BTC": "<:btc:1469015570296082676>",
    "BNB": "<:binance:1469015611567902720>",
    "USDT": "<:USDT:1469015802299813973>",
    "POLYGON": "<:polygon:1469015672611930143>",
    "ETHEREUM": "<:eth:1471348196679614567>",
    "SOLANA": "<:sol:1471348529413754986>",
    "TRON": "<:tron:1471348896256229478>",
    "DOGE": "<:dogecoin:1471349003546267792>",
    "DOGECOIN": "<:dogecoin:1471349003546267792>",
    "CARDANO": "<:cardano:1471349458481713234>",
    "AVALANCHE": "<:avalanche:1471349836057149572>",
}

class Payment(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = self.load_data()

    def load_data(self) -> dict:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_emoji(self, crypto: str) -> str:
        return CRYPTO_EMOJIS.get(crypto.upper(), "")

    # ────────────────────────────────────────────────────────────────
    #  /payment-methods   → public embed, visible to everyone
    # ────────────────────────────────────────────────────────────────
    @app_commands.command(name="payment-methods", description="Show all payment methods accepted in this server")
    async def payment_methods(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)

        if guild_id not in self.data or not self.data[guild_id]:
            embed = discord.Embed(
                title="Payment Methods",
                description="No payment methods have been set up yet.",
                color=discord.Color.dark_grey()
            )
            embed.set_footer(text="Admins can add methods with /payment-method add")
            return await interaction.response.send_message(embed=embed)

        lines = []
        for i, (crypto, address) in enumerate(sorted(self.data[guild_id].items()), 1):
            emoji = self.get_emoji(crypto)
            # You can change → to • or : or whatever separator you prefer
            line = f"{i}. {emoji} **{crypto}** → `{address}`"
            lines.append(line)

        embed = discord.Embed(
            title="Payment Methods",
            description="\n".join(lines) or "No methods added.",
            color=discord.Color.blurple()  # 0x5865F2 if you prefer hex
        )
        embed.set_footer(text=f"Server: {interaction.guild.name}")

        await interaction.response.send_message(embed=embed)

    # ────────────────────────────────────────────────────────────────
    #  /payment-method-add   → admin only, ephemeral
    # ────────────────────────────────────────────────────────────────
    @app_commands.command(name="payment-method-add", description="Add or update a payment method (admin only)")
    @app_commands.describe(
        crypto_name="Short name of the cryptocurrency (BTC, USDT, SOL, etc.)",
        address="Your receiving wallet address"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def add(self, interaction: discord.Interaction, crypto_name: str, address: str):
        guild_id = str(interaction.guild_id)
        crypto = crypto_name.upper().strip()
        addr = address.strip()

        if guild_id not in self.data:
            self.data[guild_id] = {}

        self.data[guild_id][crypto] = addr
        self.save_data()

        emoji = self.get_emoji(crypto)
        embed = discord.Embed(
            title="Payment Method Added",
            description=f"{emoji} **{crypto}** → `{addr}`",
            color=discord.Color.green()
        )
        embed.set_footer(text="Updated • /payment-methods to view all")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ────────────────────────────────────────────────────────────────
    #  /payment-method-remove   → admin only, ephemeral
    # ────────────────────────────────────────────────────────────────
    @app_commands.command(name="payment-method-remove", description="Remove a payment method (admin only)")
    @app_commands.describe(
        crypto_name="The crypto symbol to remove (e.g. BTC, USDT, LTC)"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def remove(self, interaction: discord.Interaction, crypto_name: str):
        guild_id = str(interaction.guild_id)
        crypto = crypto_name.upper().strip()

        if guild_id not in self.data or crypto not in self.data[guild_id]:
            embed = discord.Embed(
                title="Not Found",
                description=f"No **{crypto}** payment method is currently set.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        del self.data[guild_id][crypto]

        # Clean up empty guild entry
        if not self.data[guild_id]:
            self.data.pop(guild_id, None)

        self.save_data()

        embed = discord.Embed(
            title="Payment Method Removed",
            description=f"**{crypto}** has been removed from the list.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Use /payment-methods to see the updated list")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Payment(bot))