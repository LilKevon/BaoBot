
import os
import re
import random
import math
import time
from pathlib import Path

import discord
from discord.ext import commands
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from discord.ext import commands, tasks
from datetime import datetime
from zoneinfo import ZoneInfo



load_dotenv()


PING_CHANNEL_ID = 1561635601684369459

# User ID -> Winning weight
USER_WEIGHTS = {
    1158232274349850724: 1000,  
    357642743662772225: 1 
}

DEFAULT_WEIGHT = 50

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

TARGET_USER_ID = 357642743662772225
# TARGET_USER_ID = 1158232274349850724
REPLY_CHANCE = 0.05

RANDOM_RESPONSES = [
    "Nobody asked.",
    "Interesting opinion. Unfortunately, bao.",
    "Bro is NOT cooking",
    "I'm watching you.",
    "That's crazy.",
    "Skill issue.",
    "🥟"
]

REPLY_COOLDOWN = 300

last_random_reply = 0


TRIGGERS = {
    "bao": "Sam Buh",
    "BBB": "ButtBoyBao"
}

@bot.event
async def on_ready():
    print(f"BaoBot is online as {bot.user}!")

    if not monitor_ping.is_running():
        monitor_ping.start()


@bot.event
async def on_message(message):
    global last_random_reply

    if message.author.bot:
        return

    # Keyword triggers
    for trigger, response in TRIGGERS.items():
        if re.search(
            rf"\b{re.escape(trigger)}\b",
            message.content,
            re.IGNORECASE
        ):
            await message.channel.send(response)

    # Random responses to target user
    if message.author.id == TARGET_USER_ID:
        current_time = time.monotonic()

        cooldown_finished = (
            current_time - last_random_reply >= REPLY_COOLDOWN
        )

        if cooldown_finished and random.random() < REPLY_CHANCE:
            response = random.choice(RANDOM_RESPONSES)

            await message.reply(
                response,
                mention_author=False
            )

            last_random_reply = time.monotonic()

    await bot.process_commands(message)





BAO_EMOJI = "<:sam:1189448163157872720>"


MAX_HEIGHT = 10


@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"Pong! {latency}ms")


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def triangle(ctx):
    height = random.randint(3, 8)
    rows = []

    for i in range(1, height + 1):
        # Two spaces per missing emoji
        padding = "  " * (height - i)

        # Separate emojis with spaces
        row = padding + " ".join([BAO_EMOJI] * i)
        rows.append(row)

    structure = "\n".join(rows)

    await ctx.send(structure)


@bot.command()
async def stack(ctx):
    height = random.randint(1, MAX_HEIGHT)

    structure = "\n".join(
        BAO_EMOJI for _ in range(height)
    )

    await ctx.send(structure)



@bot.command()
async def pyramid(ctx):
    height = random.randint(1, MAX_HEIGHT)

    rows = []

    for i in range(1, height + 1):
        row = BAO_EMOJI * i
        rows.append(row)

    structure = "\n".join(rows)

    await ctx.send(structure)

@bot.command()
async def buttboy(ctx):
    await ctx.send("Sam Bao is a ButtBoy!")





@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def circle(ctx):
    radius = random.randint(2, 5)
    rows = []

    for y in range(-radius, radius + 1):
        row = []

        for x in range(-radius, radius + 1):
            distance = math.sqrt(x*x + y*y)

            if abs(distance - radius) < 0.5:
                row.append(BAO_EMOJI)
            else:
                row.append("　")

        rows.append("".join(row).rstrip())

    structure = "\n".join(rows)

    if len(structure) <= 2000:
        await ctx.send(structure)







@bot.command()
async def performance(ctx):
    image_path = Path(__file__).parent / "files" / "pictures" / "performance.png"

    await ctx.send(file=discord.File(image_path))







@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def diff(ctx, user1: discord.Member, user2: discord.Member):

    if user1.id == user2.id:
        await ctx.send("Bro is fighting himself 💀")
        return


    weight1 = USER_WEIGHTS.get(user1.id, DEFAULT_WEIGHT)
    weight2 = USER_WEIGHTS.get(user2.id, DEFAULT_WEIGHT)

    winner = random.choices(
        [user1, user2],
        weights=[weight1, weight2],
        k=1
    )[0]

    loser = user2 if winner == user1 else user1


    severity = random.randint(0, 100)

    if severity <= 10:
        verdict = "NEGATIVE DIFF"
    elif severity <= 25:
        verdict = "NO DIFF"
    elif severity <= 40:
        verdict = "LOW DIFF"
    elif severity <= 60:
        verdict = "MID DIFF"
    elif severity <= 80:
        verdict = "HIGH DIFF"
    else:
        verdict = "EXTREME DIFF"



    await ctx.send(
        f"**{winner.display_name} DIFFS {loser.display_name}**\n"
        f"**Diff Severity:** {severity}%\n"
        f"**Verdict:** {verdict}"
    )




@bot.command()
@commands.guild_only()
async def join(ctx):
    # Check if user is in a voice channel
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Join a VC first")
        return

    channel = ctx.author.voice.channel

    if ctx.voice_client:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()

    await ctx.send("")


@bot.command()
@commands.guild_only()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("I'm not in a VC")




SOUNDS_DIR = Path(__file__).parent / "files" / "sounds"

@bot.command()
@commands.guild_only()
@commands.cooldown(1, 15, commands.BucketType.guild)
async def sound(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Join a VC first 💀")
        return

    channel = ctx.author.voice.channel
    sound_path = SOUNDS_DIR / "bao.mp3"

    if not sound_path.is_file():
        await ctx.send("Sound file missing!")
        return

    # Avoid interfering with another playback
    if ctx.voice_client:
        await ctx.send("BaoBot is already in a VC!")
        return

    vc = None

    try:
        vc = await channel.connect()

        # Play the audio file
        source = discord.FFmpegPCMAudio(str(sound_path))
        vc.play(source)

        # Wait for playback to finish
        while vc.is_playing():
            await asyncio.sleep(0.2)

    except Exception as e:
        print(f"Voice error: {e}")
        await ctx.send("Failed to play the sound.")

    finally:
        if vc and vc.is_connected():
            await vc.disconnect()





ping_message = None

@tasks.loop(seconds=3)
async def monitor_ping():
    global ping_message

    channel = bot.get_channel(PING_CHANNEL_ID)

    if channel is None:
        return

    # Get current time in Eastern Time
    now = datetime.now(ZoneInfo("America/Toronto"))

    formatted_date = now.strftime("%B %d, %Y")
    formatted_time = now.strftime("%I:%M:%S %p %Z")

    latency = round(bot.latency * 1000)

    embed = discord.Embed(
        title="🥟 BaoBot Backend Monitor",
        color=discord.Color.green(),
        timestamp=now
    )

    embed.add_field(
        name="📡 Gateway Ping",
        value=f"`{latency} ms`",
        inline=True
    )

    embed.add_field(
        name="🟢 Status",
        value="Online",
        inline=True
    )

    embed.add_field(
        name="📅 Date",
        value=formatted_date,
        inline=False
    )

    embed.add_field(
        name="🕒 Time (Eastern)",
        value=formatted_time,
        inline=False
    )

    embed.set_footer(
        text="BaoBot • Live Backend Monitor"
    )

    try:
        if ping_message is None:
            ping_message = await channel.send(embed=embed)
        else:
            await ping_message.edit(embed=embed)

    except discord.NotFound:
        ping_message = await channel.send(embed=embed)

    except (discord.Forbidden, discord.HTTPException) as e:
        print(f"Ping monitor error: {e}")


@monitor_ping.before_loop
async def before_monitor_ping():
    await bot.wait_until_ready()

async def main():
    async with bot:
        # await bot.load_extension("cogs.gacha")
        await bot.load_extension("cogs.monitoring")
        await bot.start(os.environ["DISCORD_BOT_TOKEN"])

