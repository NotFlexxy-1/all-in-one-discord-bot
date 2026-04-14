import discord
from discord import app_commands
from discord.ext import commands

NUMBER_EMOJIS = [
    "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
    "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟", "🆙"
]

class Polls(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="poll",
        description="Create a poll with up to 11 options"
    )
    @app_commands.describe(
        question="Poll question",
        option1="Option 1",
        option2="Option 2",
        option3="Option 3",
        option4="Option 4",
        option5="Option 5",
        option6="Option 6",
        option7="Option 7",
        option8="Option 8",
        option9="Option 9",
        option10="Option 10",
        option11="Option 11"
    )
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: str | None = None,
        option4: str | None = None,
        option5: str | None = None,
        option6: str | None = None,
        option7: str | None = None,
        option8: str | None = None,
        option9: str | None = None,
        option10: str | None = None,
        option11: str | None = None,
    ):
        options = [
            option1, option2, option3, option4, option5,
            option6, option7, option8, option9, option10, option11
        ]

        options = [o for o in options if o is not None]

        if len(options) < 2:
            return await interaction.response.send_message(
                "❌ You need at least **2 options**.",
                ephemeral=True
            )

        description = ""
        for i, opt in enumerate(options):
            description += f"{NUMBER_EMOJIS[i]} {opt}\n"

        embed = discord.Embed(
            title="📊 Poll",
            description=f"**{question}**\n\n{description}",
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Poll by {interaction.user}")

        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()

        for i in range(len(options)):
            await msg.add_reaction(NUMBER_EMOJIS[i])

async def setup(bot: commands.Bot):
    await bot.add_cog(Polls(bot))
