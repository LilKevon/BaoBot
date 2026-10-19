
import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
import psutil
from discord.ext import commands, tasks


BASE_DIR = Path(__file__).resolve().parent.parent

# Change to 3 for faster updates, or 30 for efficiency
UPDATE_INTERVAL = 30

EASTERN = ZoneInfo("America/Toronto")


class Monitoring(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.channel_id = int(
            os.environ["MONITOR_CHANNEL_ID"]
        )

        # Separate dashboard state for each Discord application
        self.state_file = None
        self.dashboard_message = None

        self.started_at = time.monotonic()
        self.command_count = 0

        # Monitor this Python process only
        self.process = psutil.Process(os.getpid())
        self.process.cpu_percent(interval=None)

        self.monitor_loop.change_interval(
            seconds=UPDATE_INTERVAL
        )

    async def cog_load(self):
        self.monitor_loop.start()

    async def cog_unload(self):
        self.monitor_loop.cancel()

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        self.command_count += 1

    def format_uptime(self):
        seconds = int(time.monotonic() - self.started_at)

        days, remaining = divmod(seconds, 86400)
        hours, remaining = divmod(remaining, 3600)
        minutes, seconds = divmod(remaining, 60)

        return (
            f"{days}d {hours}h "
            f"{minutes}m {seconds}s"
        )

    def create_embed(self):
        now = datetime.now(EASTERN)

        latency = round(self.bot.latency * 1000)

        ram_mb = (
            self.process.memory_info().rss / (1024 ** 2)
        )

        cpu = self.process.cpu_percent(interval=None)

        embed = discord.Embed(
            title="🥟 BaoBot Backend Dashboard",
            description="Live system and Discord connection metrics",
            color=discord.Color.green(),
            timestamp=now
        )

        embed.add_field(
            name="🟢 Status",
            value="Online",
            inline=True
        )

        embed.add_field(
            name="📡 Gateway Ping",
            value=f"`{latency} ms`",
            inline=True
        )

        embed.add_field(
            name="⏱️ Uptime",
            value=self.format_uptime(),
            inline=True
        )

        embed.add_field(
            name="🧠 RAM Usage",
            value=f"`{ram_mb:.1f} MB`",
            inline=True
        )

        embed.add_field(
            name="⚙️ CPU Usage",
            value=f"`{cpu:.1f}%`",
            inline=True
        )

        embed.add_field(
            name="🤖 Commands Executed",
            value=f"`{self.command_count:,}`",
            inline=True
        )

        embed.add_field(
            name="📅 Date",
            value=now.strftime("%B %d, %Y"),
            inline=True
        )

        embed.add_field(
            name="🕒 Time (Eastern)",
            value=now.strftime("%I:%M:%S %p %Z"),
            inline=True
        )

        embed.set_footer(
            text=f"BaoBot Monitor • Refreshes every {UPDATE_INTERVAL}s"
        )

        return embed

    def read_message_id(self):
        if not self.state_file.exists():
            return None

        try:
            data = json.loads(
                self.state_file.read_text(encoding="utf-8")
            )

            if data.get("channel_id") != self.channel_id:
                return None

            return int(data["message_id"])

        except (OSError, ValueError, KeyError, TypeError):
            return None

    def save_message_id(self, message_id):
        data = {
            "channel_id": self.channel_id,
            "message_id": message_id
        }

        temp_file = self.state_file.with_suffix(".tmp")

        temp_file.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )

        temp_file.replace(self.state_file)

    async def find_dashboard(self, channel):
        # First try the saved message ID
        message_id = self.read_message_id()

        if message_id:
            try:
                message = await channel.fetch_message(message_id)

                if message.author.id == self.bot.user.id:
                    return message

            except discord.NotFound:
                pass

        # Recover an older dashboard if no saved ID works
        async for message in channel.history(limit=100):
            if message.author.id != self.bot.user.id:
                continue

            for embed in message.embeds:
                if embed.title == "🥟 BaoBot Backend Dashboard":
                    return message

        return None

    @tasks.loop(seconds=30)
    async def monitor_loop(self):
        try:
            channel = self.bot.get_channel(self.channel_id)

            if channel is None:
                channel = await self.bot.fetch_channel(
                    self.channel_id
                )

            if self.dashboard_message is None:
                self.dashboard_message = (
                    await self.find_dashboard(channel)
                )

            embed = self.create_embed()

            if self.dashboard_message is None:
                self.dashboard_message = await channel.send(
                    embed=embed
                )
            else:
                try:
                    await self.dashboard_message.edit(
                        embed=embed
                    )

                except discord.NotFound:
                    self.dashboard_message = (
                        await channel.send(embed=embed)
                    )

            self.save_message_id(
                self.dashboard_message.id
            )

        except (
            discord.Forbidden,
            discord.HTTPException,
            OSError
        ) as exc:
            print(f"Dashboard update failed: {exc}")

    @monitor_loop.before_loop
    async def before_monitor_loop(self):
        await self.bot.wait_until_ready()

        # Discord identity determines the saved state filename
        self.state_file = (
            BASE_DIR
            / f"dashboard-{self.bot.user.id}.json"
        )


async def setup(bot):
    await bot.add_cog(Monitoring(bot))
