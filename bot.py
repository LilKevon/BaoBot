
import os
import re
import discord
from discord.ext import commands
import random
import math
import time
from pathlib import Path


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
        cooldown_finished = (current_time - last_random_reply >= REPLY_COOLDOWN)

        if cooldown_finished and random.random() < REPLY_CHANCE:    
            response = random.choice(RANDOM_RESPONSES)
            await message.channel.send(response)
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



PICTURES_DIR = Path(__file__).parent / "pictures"




@bot.command()
async def performance(ctx):
    image_path = Path(__file__).parent / "files" / "pictures" / "performance.png"

    await ctx.send(file=discord.File(image_path))


bot.run(os.environ["DISCORD_BOT_TOKEN"])

