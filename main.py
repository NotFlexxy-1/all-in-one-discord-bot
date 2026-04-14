import discord
from discord.ext import commands
import os
import asyncio
from config import TOKEN, PREFIX

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True
INTENTS.guilds = True

class LegendaryBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(PREFIX),
            intents=INTENTS,
            help_command=None
        )

    async def setup_hook(self):
        # Load all cogs
        for file in os.listdir("./cogs"):
            if file.endswith(".py"):
                await self.load_extension(f"cogs.{file[:-3]}")
                print(f"✅ Loaded cog: {file}")

        # Sync slash commands globally
        await self.tree.sync()
        print("🌍 Slash commands synced globally")

bot = LegendaryBot()

@bot.event
async def on_ready():
    print(f"🔥 Logged in as {bot.user} ({bot.user.id})")
    print("🚀 Legendary bot is ONLINE")

# Prefix test command
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! `{round(bot.latency * 1000)}ms`")

async def main():
    async with bot:
        await bot.start(TOKEN)

asyncio.run(main())
