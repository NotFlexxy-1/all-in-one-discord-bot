import discord
from discord.ext import commands
import sqlite3
import random
import time

DB = "data.db"

def get_db():
    return sqlite3.connect(DB)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with get_db() as db:
            db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                cash INTEGER DEFAULT 0,
                last_daily INTEGER DEFAULT 0
            )""")

    def ensure(self, user_id: int):
        with get_db() as db:
            db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

    @commands.command(name="cash")
    async def cash(self, ctx):
        self.ensure(ctx.author.id)
        cash = get_db().execute(
            "SELECT cash FROM users WHERE user_id=?",
            (ctx.author.id,)
        ).fetchone()[0]
        await ctx.send(f"💰 **{ctx.author.name}**, you have **{cash}** coins")

    @commands.command(name="daily")
    async def daily(self, ctx):
        self.ensure(ctx.author.id)
        now = int(time.time())
        last = get_db().execute(
            "SELECT last_daily FROM users WHERE user_id=?",
            (ctx.author.id,)
        ).fetchone()[0]

        if now - last < 86400:
            return await ctx.send("⏳ Daily already claimed")

        reward = random.randint(200, 500)
        with get_db() as db:
            db.execute(
                "UPDATE users SET cash=cash+?, last_daily=? WHERE user_id=?",
                (reward, now, ctx.author.id)
            )

        await ctx.send(f"🎁 You received **{reward}** coins!")

    @commands.command(name="battle")
    async def battle(self, ctx, member: discord.Member):
        self.ensure(ctx.author.id)
        self.ensure(member.id)

        win = random.choice([ctx.author.id, member.id])
        reward = random.randint(100, 300)

        with get_db() as db:
            db.execute(
                "UPDATE users SET cash=cash+? WHERE user_id=?",
                (reward, win)
            )

        winner = ctx.author if win == ctx.author.id else member
        await ctx.send(f"⚔️ **{winner.mention}** won **{reward}** coins!")

    @commands.command(name="top")
    async def top(self, ctx):
        rows = get_db().execute(
            "SELECT user_id, cash FROM users ORDER BY cash DESC LIMIT 10"
        ).fetchall()

        text = ""
        for i, (uid, cash) in enumerate(rows, start=1):
            user = self.bot.get_user(uid)
            text += f"**{i}.** {user} — {cash}\n"

        embed = discord.Embed(
            title="🏆 Top Richest",
            description=text or "No data",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
