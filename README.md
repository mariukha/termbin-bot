# Termbin Telegram Bot 🤖

A simple Telegram bot that saves text messages to [termbin.com](https://termbin.com) and returns the link.

## How it works

1. You send a text message to the bot
2. The bot sends it to termbin.com (like `echo "text" | nc termbin.com 9999`)
3. The bot returns the link to your saved text

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/termbin-bot.git
cd termbin-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Get a bot token:
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` command
   - Follow instructions and copy the token

4. Set the environment variable:
```bash
export TERMBIN_BOT_TOKEN="your_token_here"
```

## Usage

```bash
python3 bot.py
```

### Commands
- `/start` - Welcome message
- Send any text - Get a termbin link
