
# 🥟 BaoBot

A Discord bot built with Python and `discord.py`, featuring a collectible Bao-themed gacha system, player economy, trading, interactive inventories, and a collection of questionable commands.

Originally created as a small joke bot for friends, BaoBot has evolved into a full collectible-card experience.

## 🎰 Features

### Gacha System
- Collect unique Bao-themed cards with randomized rarities.
- Eight rarity tiers: Common, Uncommon, Rare, Epic, Legendary, Mythical, Divine, and Peebing Cool.
- Every card can be obtained at any rarity.
- Independent 1% chance to obtain shiny variants.
- Tiered pity system with guaranteed Rare+, Epic+, Legendary+, and Mythical+ pulls.
- Single and multi-roll commands, supporting up to 10 cards at once.

### 🪙 BaoCoin Economy
- Five regenerating free rolls, replenished at one roll per minute.
- Earn BaoCoins by selling unwanted cards.
- Purchase additional rolls for 100 BaoCoins each.
- Claim daily and weekly currency rewards.
- Purchased rolls are stored separately from free rolls.

### 🃏 Inventory and Trading
- Persistent SQLite card collections.
- Interactive inventory browser with dropdown navigation.
- Collection overview displaying rarity distribution and statistics.
- Inspect individual card instances.
- View another player's inventory.
- Sell cards individually or in batches.
- Sell newly pulled cards using an interactive button.
- Trade cards directly with other players using Accept/Decline buttons.
- Global collections shared across Discord servers.

### 🎭 Fun Commands
- Random responses and keyword-triggered messages.
- User-versus-user diff comparisons.
- Emoji triangles, pyramids, circles, and stacks.
- Image and soundbite commands.
- Voice channel support.

### ⚙️ Additional Features
- Interactive help menu.
- Unknown-command detection and typo suggestions.
- Live backend monitoring dashboard.
- Separate development and production environments.
- Local administrative control utility.

---

## 📜 Command Reference

### 🎰 Gacha

| Command | Description |
|---|---|
| `!roll` | Pull one random Bao card |
| `!multiroll [2-10]` | Pull multiple cards, defaulting to 10 |
| `!pity` | View rarity pity progression |

### 🪙 Economy

| Command | Description |
|---|---|
| `!balance` / `!bal` | View BaoCoins and available rolls |
| `!buyroll <amount>` | Purchase rolls for 100 BC each |
| `!daily` | Claim 200 BaoCoins every 24 hours |
| `!weekly` | Claim 1,000 BaoCoins every 7 days |
| `!rewards` | Check reward cooldowns |
| `!sell <instance_id>` | Sell an individual card |
| `!multisell <id1> <id2> ...` | Sell multiple cards simultaneously |

### 🃏 Inventory and Trading

| Command | Description |
|---|---|
| `!inventory` / `!inv` | Open your inventory |
| `!inv @user` | View another player's inventory |
| `!inspect <instance_id>` | Inspect an owned card |
| `!collection` / `!cards` | Inventory shortcuts |
| `!trade @user <your_id> <their_id>` | Propose a card-for-card trade |

### 🎭 Fun

| Command | Description |
|---|---|
| `!diff @user1 @user2` | Compare two users |
| `!triangle` | Generate an emoji triangle |
| `!pyramid` | Generate an emoji pyramid |
| `!circle` | Generate an emoji circle |
| `!stack` | Generate an emoji stack |
| `!buttboy` | Classic BaoBot response |
| `!performance` | Send the performance image |
| `!join` | Join your voice channel |
| `!leave` | Leave the voice channel |
| `!sound` | Play a soundbite |
| `!ping` | Display bot latency |
| `!help` | Open the interactive command menu |

---

## 💎 Rarity System

Cards are assigned a rarity independently of their image when pulled.

| Rarity | Description |
|---|---|
| ⚪ Common | Most frequently obtained |
| 🟢 Uncommon | Slightly less common |
| 🔵 Rare | A more valuable pull |
| 🟣 Epic | An exciting find |
| 🟡 Legendary | A highly desirable card |
| 🔴 Mythical | An exceptionally rare pull |
| 💎 Divine | Jackpot-tier rarity |
| 🥟 Peebing Cool | The ultimate collectible |

### Pity System

| Rarity | Hard Pity |
|---|---|
| Rare+ | 15 unsuccessful pulls |
| Epic+ | 50 unsuccessful pulls |
| Legendary+ | 150 unsuccessful pulls |
| Mythical+ | 1,500 unsuccessful pulls |
| Divine | No pity |
| Peebing Cool | No pity |

Higher-rarity drops reset applicable lower-rarity pity counters.

Rarity probabilities are configured through `RARITY_WEIGHTS` in `cogs/gacha.py`.

---

## 🚀 Installation

### Requirements

- Python 3.13 or a compatible version
- Discord bot application and token
- FFmpeg for voice functionality

### 1. Clone the Repository

```bash
git clone https://github.com/LilKevon/BaoBot.git
cd BaoBot
```

### 2. Install Dependencies

```bash
py -m pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create `.env` for production and `.env.dev` for development.

Example `.env`:

```dotenv
DISCORD_BOT_TOKEN=your_production_token
BOT_ENV=production
MONITOR_CHANNEL_ID=your_channel_id
```

Example `.env.dev`:

```dotenv
DISCORD_BOT_TOKEN=your_development_token
BOT_ENV=development
MONITOR_CHANNEL_ID=your_dev_channel_id
```

**Never commit environment files or share your Discord bot tokens.**

Enable the Message Content Intent in the Discord Developer Portal for both bot applications.

### 4. Run BaoBot

Production:

```bash
py bot.py
```

Development:

```bash
py botdev.py
```

The two environments use separate SQLite databases:

- Production: `baobot.db`
- Development: `baobot-dev.db`

---

## 📁 Project Structure

```text
BaoBot/
├── bot.py                 # Production bot
├── botdev.py              # Development launcher
├── database.py            # SQLite persistence and economy
├── control.py             # Local administrative utilities
├── requirements.txt
├── README.md
├── cogs/
│   ├── gacha.py           # Gacha, pity, and economy commands
│   ├── inventory.py       # Interactive inventory viewer
│   ├── card_sale.py       # Card sale buttons
│   ├── trading.py         # Player trading
│   ├── rewards.py         # Daily and weekly rewards
│   ├── help_menu.py       # Interactive command menu
│   └── monitoring.py      # Backend monitoring dashboard
├── data/
│   └── cards.json         # Card catalogue
└── files/
    ├── cards/             # Collectible card images
    ├── pictures/          # Other bot images
    └── sounds/            # Audio files
```

---

## 🛠️ Development Utilities

BaoBot includes a local administrative utility (`control.py`) for testing and managing the economy.

Run it with:

```bash
py control.py
```

Example operations:

```text
give coins 10000
give rolls 100
give card bao_001 divine shiny
give random peebing_cool shiny
set pity legendary 149
reset pity
inspect
```

This utility is intended for local administration and testing, not regular Discord users.

---

## 🗺️ Roadmap

### Completed

- [x] Basic Discord commands and responses
- [x] Collectible card gacha
- [x] Shiny variants and weighted rarities
- [x] SQLite card collections
- [x] BaoCoin economy
- [x] Regenerating free rolls
- [x] Daily and weekly rewards
- [x] Multi-roll system
- [x] Tiered pity system
- [x] Interactive inventory browser
- [x] Player-to-player trading
- [x] Individual and batch selling
- [x] Interactive help menu
- [x] Unknown-command error handling
- [x] Backend monitoring dashboard

### Planned

- [ ] Daily quests and achievements
- [ ] Collection milestones
- [ ] Multi-card trading
- [ ] Trade history
- [ ] Leaderboards
- [ ] Special events and limited-time cards
- [ ] Additional card sets
- [ ] Economy balancing and analytics
- [ ] Improved inventory filtering and search

---

## ⚠️ Notes

BaoBot is a personal project developed primarily for entertainment and experimentation.

The economy uses fictional BaoCoins with no real-world monetary value.

Card data, balances, and pity progression are stored locally in SQLite.

Database files, credentials, and environment configuration should never be committed to version control.

---

## 👨‍💻 Author

Developed by [LilKevon](https://github.com/LilKevon).

Built with Python, discord.py, SQLite, and an unreasonable amount of Bao. 🥟
