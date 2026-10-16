# 🥟 BaoBot

A chaotic Discord bot built with Python, designed to bring questionable humour, random interactions, and unnecessary amounts of Bao emojis to your Discord server.

## Features

- **Keyword Detection:** Automatically responds when specific words or phrases are mentioned.
- **Random Reactions:** Occasionally replies to messages with randomized responses.
- **Emoji Formations:** Generates randomly sized stacks, pyramids, and circles using custom Discord emojis.
- **Image & GIF Responses:** Sends reaction images, memes, and GIFs.
- **Custom Commands:** Includes commands for various interactions and inside jokes.

### Commands

| Command | Description |
|---|---|
| `!stack` | Generates a random stack of Bao emojis. |
| `!pyramid` | Generates a random pyramid of Bao emojis. |
| `!circle` | Generates a random circle of Bao emojis. |
| `!picture` | Sends a random image from the picture bank. |
| `!performance` | Sends the performance meme. |

*Commands and features are subject to change as BaoBot evolves.*

## Tech Stack

- **Language:** Python
- **Library:** discord.py
- **Configuration:** python-dotenv
- **Version Control:** Git & GitHub

## Getting Started

### Prerequisites

- Python 3.10 or newer
- A Discord bot token
- A Discord application with Message Content Intent enabled

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/YOUR_USERNAME/BaoBot.git
   cd BaoBot
   ```

2. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Create a `.env` file in the project directory:

   ```env
   DISCORD_BOT_TOKEN=YOUR_BOT_TOKEN
   ```

4. Start BaoBot:

   ```bash
   python bot.py
   ```

Make sure your bot has the appropriate permissions to view channels, send messages, and attach files.

## Project Structure

```text
BaoBot/
├── bot.py
├── .env
├── .gitignore
├── requirements.txt
├── README.md
└── files/
    └── pictures/
        └── performance.png
```

## Future Plans

- More randomized interactions and custom commands
- Additional GIF and image reactions
- User-specific interactions
- A virtual currency and economy system
- Player profiles and progression
- A multiplayer combat simulator

## Disclaimer

BaoBot is a personal project created for entertainment and experimentation. It is not affiliated with Discord.

---

*Made with Python, questionable decisions, and an unreasonable amount of Bao.* 🥟
