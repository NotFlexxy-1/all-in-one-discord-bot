import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import aiosqlite
from io import BytesIO

DB = "data.db"

TICKET_OPTIONS = {
    "support": "🎧 Support",
    "rewards": "🎁 Claim Rewards",
    "purchase": "🛒 Purchase",
    "partner": "🤝 Partnership",
    "ytapply": "📹 YT Apply",
    "staffapply": "🛡️ Staff Apply"
}

TICKET_DESCRIPTIONS = {
    "support": "Report bugs, ask questions, get help with the server.",
    "rewards": "Claim giveaway rewards, invite rewards or boost rewards.",
    "purchase": "Inquiries about buying vps, minecraft servers or etc.",
    "partner": "Server partnership requests, collaborations.",
    "ytapply": "Apply for YouTuber Role (Must Make a Video for us)",
    "staffapply": "Apply to join the staff team (moderator, helper, etc.)"
}


# ===================== HELPERS =====================

async def get_creator_id(channel_id: int) -> int | None:
    """Returns the ticket creator's user ID or None if not found."""
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT creator_id FROM tickets WHERE channel_id = ?",
            (channel_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


# ===================== TRANSCRIPT SYSTEM =====================

async def create_transcript(channel: discord.TextChannel) -> discord.File:
    """Creates a clean text transcript of the entire ticket channel."""
    messages = []
    async for message in channel.history(limit=None, oldest_first=True):
        timestamp = message.created_at.strftime("%b %d, %Y %I:%M %p")
        author = str(message.author)
        if message.author.bot:
            author += " (Bot)"
        content = message.content or ""
        if message.embeds:
            content += "\n[Embed Message]"
        if message.attachments:
            atts = ", ".join([a.filename for a in message.attachments])
            content += f"\n[Attachments: {atts}]"
        if message.stickers:
            content += "\n[Sticker]"
        line = f"[{timestamp}] {author}: {content}"
        messages.append(line)
    transcript_text = "\n".join(messages) or "No messages were found in this ticket."
    return discord.File(
        BytesIO(transcript_text.encode("utf-8")),
        filename=f"transcript-{channel.name.replace(' ', '-')}.txt"
    )


async def send_transcript_to_creator(channel: discord.TextChannel, interaction: discord.Interaction) -> int | None:
    """Sends the ticket transcript to the creator via DM and returns creator_id if found."""
    creator_id = await get_creator_id(channel.id)
    if not creator_id:
        return None
    try:
        transcript_file = await create_transcript(channel)
        creator = interaction.client.get_user(creator_id)
        if not creator:
            creator = await interaction.client.fetch_user(creator_id)
        if creator:
            await creator.send(
                content=(
                    f"📄 **Your Ticket Transcript**\n"
                    f"**Channel:** `{channel.name}`\n"
                    f"**Action by:** {interaction.user} ({interaction.user.id})\n"
                    f"Thank you for using our support system!"
                ),
                file=transcript_file
            )
            return creator_id
    except Exception:
        return creator_id
    return None


# ===================== DROPDOWN =====================

class TicketSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [
            discord.SelectOption(
                label=label,
                value=key,
                description=TICKET_DESCRIPTIONS[key]
            )
            for key, label in TICKET_OPTIONS.items()
        ]
        super().__init__(
            placeholder="🎫 Select ticket category...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket:dropdown:main"
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        cog = self.bot.get_cog("Tickets")
        if cog:
            await cog.create_ticket(interaction, self.values[0])


class TicketPanelView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.add_item(TicketSelect(bot))


# ===================== BUTTONS =====================

class ClaimButton(discord.ui.Button):
    def __init__(self, channel_id: int):
        super().__init__(label="✅ Claim", style=discord.ButtonStyle.blurple, custom_id=f"ticket:claim:{channel_id}")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        if channel.name.startswith("✅"):
            return await interaction.followup.send("Already claimed.", ephemeral=True)
        new_name = channel.name.replace("🎫-", "✅-")
        await channel.edit(name=new_name, topic=f"Claimed by {interaction.user}")
        await channel.send(f"{interaction.user.mention} claimed this ticket.")
        await interaction.followup.send("Ticket claimed.", ephemeral=True)


class LockButton(discord.ui.Button):
    def __init__(self, channel_id: int):
        super().__init__(label="🔒 Lock", style=discord.ButtonStyle.red, custom_id=f"ticket:lock:{channel_id}")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        creator_id = await get_creator_id(channel.id)
        if creator_id:
            try:
                target = discord.Object(id=creator_id)
                await channel.set_permissions(
                    target,
                    send_messages=False,
                    read_message_history=True,
                    view_channel=True
                )
                await channel.send(
                    "🔒 **Ticket locked**\n"
                    "Only staff can reply now. The ticket creator can no longer send messages."
                )
                await interaction.followup.send("✅ Ticket locked (creator can no longer chat).", ephemeral=True)
                return
            except discord.Forbidden:
                pass

        await channel.send("🔒 Ticket locked (default behavior).")
        await interaction.followup.send("Locked.", ephemeral=True)


class UnlockButton(discord.ui.Button):
    def __init__(self, channel_id: int):
        super().__init__(label="🔓 Unlock", style=discord.ButtonStyle.green, custom_id=f"ticket:unlock:{channel_id}")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        creator_id = await get_creator_id(channel.id)
        if creator_id:
            try:
                target = discord.Object(id=creator_id)
                await channel.set_permissions(
                    target,
                    send_messages=True,
                    read_message_history=True,
                    view_channel=True
                )
                await channel.send(
                    "🔓 **Ticket unlocked**\n"
                    "The ticket creator can now send messages again."
                )
                await interaction.followup.send("✅ Ticket unlocked (creator can chat again).", ephemeral=True)
                return
            except discord.Forbidden:
                pass

        await interaction.followup.send("Unlocked.", ephemeral=True)


class CloseButton(discord.ui.Button):
    def __init__(self, channel_id: int):
        super().__init__(label="🔴 Close", style=discord.ButtonStyle.danger, custom_id=f"ticket:close:{channel_id}", row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        creator_id = await send_transcript_to_creator(channel, interaction)
        if creator_id:
            try:
                await channel.set_permissions(
                    discord.Object(id=creator_id),
                    view_channel=False,
                    send_messages=False
                )
            except discord.Forbidden:
                pass

        await channel.edit(name="🔴-closed-ticket")
        await channel.send(
            f"✅ Ticket closed by {interaction.user.mention}. "
            f"{'Transcript has been sent to the creator via DM.' if creator_id else ''}"
        )
        await interaction.followup.send("Closed.", ephemeral=True)


class DeleteButton(discord.ui.Button):
    def __init__(self, channel_id: int):
        super().__init__(label="🗑️ Delete", style=discord.ButtonStyle.gray, custom_id=f"ticket:delete:{channel_id}", row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        creator_id = await send_transcript_to_creator(channel, interaction)

        await channel.send(
            f"🗑️ Deleting in 3 seconds... "
            f"{'Transcript has been sent to the creator via DM.' if creator_id else ''}"
        )
        await asyncio.sleep(3)
        await channel.delete()


class TicketControlView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=None)
        self.add_item(ClaimButton(channel_id))
        self.add_item(LockButton(channel_id))
        self.add_item(UnlockButton(channel_id))
        self.add_item(CloseButton(channel_id))
        self.add_item(DeleteButton(channel_id))


# ===================== COG =====================

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect(DB) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ticket_staff (
                    guild_id INTEGER,
                    role_id INTEGER,
                    PRIMARY KEY (guild_id, role_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    channel_id INTEGER PRIMARY KEY,
                    creator_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL
                )
            """)
            await db.commit()

    async def get_staff_roles(self, guild_id: int):
        async with aiosqlite.connect(DB) as db:
            cursor = await db.execute("SELECT role_id FROM ticket_staff WHERE guild_id = ?", (guild_id,))
            return [row[0] async for row in cursor]

    async def create_ticket(self, interaction: discord.Interaction, option: str):
        guild = interaction.guild
        user = interaction.user

        category_name = f"{option.capitalize()} Tickets"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)

        count = sum(1 for ch in category.text_channels if ch.name.startswith("🎫-")) + 1
        channel_name = f"🎫-{option}-{user.name}-{count}".lower()

        staff_roles = await self.get_staff_roles(guild.id)
        ping_mentions = [f"<@&{rid}>" for rid in staff_roles]

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        for rid in staff_roles:
            role = guild.get_role(rid)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "INSERT OR IGNORE INTO tickets (channel_id, creator_id, guild_id) VALUES (?, ?, ?)",
                (channel.id, user.id, guild.id)
            )
            await db.commit()

        embed = discord.Embed(
            title=f"{TICKET_OPTIONS[option]} Ticket",
            description=f"{user.mention}, please describe your issue.",
            color=discord.Color.green()
        )

        content = f"{user.mention} {' '.join(ping_mentions)}" if ping_mentions else user.mention

        await channel.send(content=content, embed=embed, view=TicketControlView(channel.id))
        await interaction.response.send_message(f"Created: {channel.mention}", ephemeral=True)

    # -------- COMMANDS --------

    @app_commands.command(name="ticket", description="Post the ticket panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎫 Create Ticket",
            description="Select a category below",
            color=discord.Color.blurple()
        )
        await interaction.channel.send(embed=embed, view=TicketPanelView(self.bot))
        await interaction.response.send_message("Ticket panel posted.", ephemeral=True)

    @app_commands.command(name="ticket_add_staff", description="Add a role pinged on ticket creation")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_staff(self, interaction: discord.Interaction, role: discord.Role):
        async with aiosqlite.connect(DB) as db:
            await db.execute("INSERT OR IGNORE INTO ticket_staff VALUES (?, ?)", (interaction.guild.id, role.id))
            await db.commit()
        await interaction.response.send_message(f"✅ {role.mention} added to ticket staff.", ephemeral=True)

    @app_commands.command(name="ticket_remove_staff", description="Remove a staff role from ticket pings")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_staff(self, interaction: discord.Interaction, role: discord.Role):
        async with aiosqlite.connect(DB) as db:
            await db.execute("DELETE FROM ticket_staff WHERE guild_id = ? AND role_id = ?", (interaction.guild.id, role.id))
            await db.commit()
        await interaction.response.send_message(f"✅ {role.mention} removed from ticket staff.", ephemeral=True)


# ===================== SETUP =====================

async def setup(bot: commands.Bot):
    cog = Tickets(bot)
    await bot.add_cog(cog)
    await cog.cog_load()

    bot.add_view(TicketPanelView(bot))
    bot.add_view(TicketControlView(0))