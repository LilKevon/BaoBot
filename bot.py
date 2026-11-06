
import os
import re
import random
import math
import time
from pathlib import Path
import difflib
import logging
import sys
import asyncio

import discord
from pathlib import Path

from dotenv import load_dotenv

from discord.ext import commands, tasks
from datetime import datetime
from zoneinfo import ZoneInfo


from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

if __name__ == "__main__":
  
    load_dotenv(BASE_DIR / ".env", override=True)
    os.environ["BOT_ENV"] = "production"
else:
 
    pass
from database import initialize_database

ANNOUNCEMENT_CHANNEL_ID = 1561644432640442379

BACK_ONLINE_IMAGE = (
    Path(__file__).resolve().parent
    / "files"
    / "pictures"
    / "back_online_bao.jpg"
)





USER_WEIGHTS = {
    1158232274349850724: 1000,  
    357642743662772225: 1 
}

OWNER_IDS = {
    1158232274349850724  
}


DEFAULT_WEIGHT = 50

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

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


    if os.getenv("BOT_ENV") == "development":
        return


    if getattr(bot, "startup_announced", False):
        return

    if not BACK_ONLINE_IMAGE.is_file():
        print("Back-online image not found!")
        return

    try:
        channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)

        if channel is None:
            channel = await bot.fetch_channel(
                ANNOUNCEMENT_CHANNEL_ID
            )

        await channel.send(
            content="🥟 **Back online.**",
            file=discord.File(BACK_ONLINE_IMAGE)
        )

        bot.startup_announced = True

    except (discord.Forbidden, discord.HTTPException) as e:
        print(f"Failed to send startup announcement: {e}")


@bot.event
async def on_message(message):
    global last_random_reply

    if message.author.bot:
        return


    for trigger, response in TRIGGERS.items():
        if re.search(
            rf"\b{re.escape(trigger)}\b",
            message.content,
            re.IGNORECASE
        ):
            await message.channel.send(response)

  
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
      
        padding = "  " * (height - i)

       
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


    if ctx.voice_client:
        await ctx.send("BaoBot is already in a VC!")
        return

    vc = None

    try:
        vc = await channel.connect()

        source = discord.FFmpegPCMAudio(str(sound_path))
        vc.play(source)

     
        while vc.is_playing():
            await asyncio.sleep(0.2)

    except Exception as e:
        print(f"Voice error: {e}")
        await ctx.send("Failed to play the sound.")

    finally:
        if vc and vc.is_connected():
            await vc.disconnect()


@bot.event
async def on_command_error(ctx, error):
 
    if ctx.command is not None:
        if ctx.command.has_error_handler():
            return

        if (
            ctx.cog is not None
            and ctx.cog.has_error_handler()
        ):
            return

    if isinstance(error, commands.CommandNotFound):
        attempted = ctx.invoked_with or ""

  
        command_names = {
            name
            for name, command in bot.all_commands.items()
            if not command.hidden
        }

        matches = difflib.get_close_matches(
            attempted.lower(),
            sorted(command_names),
            n=1,
            cutoff=0.6
        )

        message = (
            f"❌ **What the peeb did you say to me?** `!{attempted}`\n"
        )

        if matches:
            message += (
                f"Are you peebing stupid? Might be `!{matches[0]}`?\n"
            )
        else:
            message += (
                "I might be BBB, "
                "but you might be the real butt boy.\n"
            )

        message += "Use `!help` to see all commands."

        await ctx.send(message)
        return

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            "⏳ **Slow down!**\n"
            f"Try again in **{error.retry_after:.1f}s**."
        )
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"❌ Missing argument: `{error.param.name}`.\n"
            "Use `!help` to check command usage."
        )
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send(
            "❌ Invalid argument or user.\n"
            "Check your input and try again."
        )
        return

    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send(
            "❌ This command only works in a server."
        )
        return

    if isinstance(error, commands.CheckFailure):
        await ctx.send(
            "❌ You can't use that command here."
        )
        return

  
    logging.exception(
        "Unexpected error in command %s",
        ctx.command,
        exc_info=(
            type(error),
            error,
            error.__traceback__
        )
    )

    await ctx.send(
        "⚠️ Something went wrong while running "
        "that command."
    )


@bot.command(name="restart")
@commands.guild_only()
async def restart(ctx):
    if ctx.author.id not in OWNER_IDS:
        await ctx.send(
            "❌ You don't have permission to restart BBB."
        )
        return

    await ctx.send("🔄 Restarting BaoBot... 🥟")

  
    async def perform_restart():
        await asyncio.sleep(1)

       
        await bot.close()

        os.execv(
            sys.executable,
            [sys.executable, *sys.argv]
        )

    asyncio.create_task(perform_restart())

@bot.command(name="LilKevon")
@commands.guild_only()
async def LilKevon(ctx):
    await ctx.send("Goated Dev")


async def main():
    initialize_database()

    async with bot:
        await bot.load_extension("cogs.monitoring")
        await bot.load_extension("cogs.gacha")
        await bot.load_extension("cogs.trading")
        await bot.load_extension("cogs.help_menu")
        await bot.load_extension("cogs.rewards")
        await bot.load_extension("cogs.dictionary")
        await bot.load_extension("cogs.slots")
        await bot.load_extension("cogs.gallery")
        await bot.start(os.environ["DISCORD_BOT_TOKEN"])


if __name__ == "__main__":
    asyncio.run(main())