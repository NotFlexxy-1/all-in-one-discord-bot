# cogs/music.py
import discord
from discord import app_commands
from discord.ext import commands
import wavelink
import asyncio
from typing import Optional, cast

class Music(commands.Cog):
    """Music System - YOUR self-hosted Lavalink"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Connect to your Lavalink"""
        await self.bot.wait_until_ready()

        nodes = [
            wavelink.Node(
                uri="http://103.43.19.68:24599",
                password="nebryxcloudlavalink"   # ← MUST BE EXACTLY same as in application.yml
            )
        ]

        await wavelink.Pool.connect(nodes=nodes, client=self.bot)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload):
        print(f"✅ Lavalink Connected Successfully!")

    # ─── Helper ───
    def get_player(self, guild: discord.Guild) -> Optional[wavelink.Player]:
        player = guild.voice_client
        return cast(wavelink.Player, player) if player else None

    # ─── COMMANDS ───
    @app_commands.command(name="play", description="Play a song or add to queue")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.send_message("🔍 Searching...", ephemeral=False)

        if not interaction.user.voice:
            return await interaction.edit_original_response(content="❌ Join a voice channel first!")

        player = self.get_player(interaction.guild)
        if not player:
            player = await wavelink.Player.create(
                channel=interaction.user.voice.channel,
                client=self.bot,
                self_deaf=True
            )
        if not player.connected:
            await player.connect()

        try:
            async with asyncio.timeout(15):
                search = await wavelink.Playable.search(query, source=wavelink.Source.YouTube)
        except asyncio.TimeoutError:
            return await interaction.edit_original_response(content="⏳ Timed out. Restart Lavalink.")
        except Exception as e:
            return await interaction.edit_original_response(content=f"❌ Error: {str(e)[:200]}")

        if not search:
            return await interaction.edit_original_response(content="❌ Nothing found! (Check YouTube is enabled in yml)")

        if isinstance(search, wavelink.Playlist):
            await player.queue.put_wait(search.tracks)
            await interaction.edit_original_response(content=f"✅ Playlist added: **{search.name}**")
        else:
            track = search[0]
            await player.queue.put_wait(track)
            await interaction.edit_original_response(content=f"✅ Added: **{track.title}**")

        if not player.playing:
            await player.play(await player.queue.get_wait())

    @app_commands.command(name="skip", description="Skip current song")
    async def skip(self, interaction: discord.Interaction):
        await interaction.response.defer()
        player = self.get_player(interaction.guild)
        if not player or not player.playing:
            return await interaction.followup.send("❌ Nothing playing.", ephemeral=True)
        await player.skip()
        await interaction.followup.send("⏭️ Skipped!")

    @app_commands.command(name="pause", description="Pause / Resume")
    async def pause(self, interaction: discord.Interaction):
        await interaction.response.defer()
        player = self.get_player(interaction.guild)
        if not player: return await interaction.followup.send("❌ Not in voice.", ephemeral=True)
        if player.paused:
            await player.resume()
            await interaction.followup.send("▶️ Resumed")
        else:
            await player.pause()
            await interaction.followup.send("⏸️ Paused")

    @app_commands.command(name="stop", description="Stop & clear queue")
    async def stop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        player = self.get_player(interaction.guild)
        if not player: return await interaction.followup.send("❌ Not in voice.", ephemeral=True)
        await player.stop()
        player.queue.clear()
        await interaction.followup.send("⏹️ Stopped.")

    @app_commands.command(name="queue", description="Show queue")
    async def queue(self, interaction: discord.Interaction):
        await interaction.response.defer()
        player = self.get_player(interaction.guild)
        if not player or player.queue.is_empty:
            return await interaction.followup.send("Queue empty.", ephemeral=True)
        q = "\n".join([f"{i+1}. {t.title}" for i, t in enumerate(player.queue)])
        await interaction.followup.send(f"**Queue ({len(player.queue)}):**\n{q}")

    @app_commands.command(name="nowplaying", description="Current song")
    async def nowplaying(self, interaction: discord.Interaction):
        await interaction.response.defer()
        player = self.get_player(interaction.guild)
        if not player or not player.playing:
            return await interaction.followup.send("❌ Nothing playing.", ephemeral=True)
        track = player.current
        embed = discord.Embed(title="🎵 Now Playing", description=f"[{track.title}]({track.uri})", color=discord.Color.green())
        embed.add_field(name="Duration", value=f"{track.length//60}:{track.length%60:02d}")
        embed.set_thumbnail(url=track.artwork)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="leave", description="Leave VC")
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.defer()
        player = self.get_player(interaction.guild)
        if not player: return await interaction.followup.send("❌ Not in voice.", ephemeral=True)
        await player.disconnect()
        await interaction.followup.send("👋 Left voice channel.")

    @app_commands.command(name="node_status", description="Lavalink status")
    async def node_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        nodes = wavelink.Pool.nodes
        if not nodes:
            return await interaction.followup.send("No nodes.", ephemeral=True)
        msg = "**Lavalink Status:**\n"
        for name, node in nodes.items():
            status = "🟢 Online" if node.is_connected() else "🔴 Offline"
            msg += f"• {name}: {status}\n"
        await interaction.followup.send(msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))