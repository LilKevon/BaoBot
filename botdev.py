
import os
import asyncio
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env.dev", override=True)

from bot import bot
from database import initialize_database


async def main():
    initialize_database()

    async with bot:
        await bot.load_extension("cogs.gacha")
        await bot.load_extension("cogs.monitoring")
        await bot.start(os.environ["DISCORD_BOT_TOKEN"])


if __name__ == "__main__":
    asyncio.run(main())
