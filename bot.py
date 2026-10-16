
import os
import re
import random
import math
import time
from pathlib import Path

import discord
from discord.ext import commands


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
    "Bro is NOT cooking 💀",
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


bot.run(os.environ["DISCORD_BOT_TOKEN"])

