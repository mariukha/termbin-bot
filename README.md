# Termbin + AI Telegram Bot

A Telegram bot that combines text sharing via [termbin.com](https://termbin.com) with AI chat capabilities.

## Features

- **Termbin Mode** (default): Send any text and get a shareable termbin.com link
- **AI Mode**: Chat with Llama 3.1 8B for coding help and Q&A

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show help message |
| `/ai` | Enter AI mode |
| `/quit` | Exit AI mode, return to Termbin |

## Setup

### 1. Get API Keys

- **Telegram Bot Token**: Get from [@BotFather](https://t.me/BotFather)
- **OpenRouter API Key**: Get from [openrouter.ai](https://openrouter.ai/keys)

### 2. Install Dependencies

```bash
pip install python-telegram-bot openai
```

### 3. Run the Bot

```bash
export TERMBIN_BOT_TOKEN="your_telegram_bot_token"
export OPENROUTER_API_KEY="your_openrouter_api_key"
python3 bot.py
```

## How It Works

1. By default, any text you send is uploaded to termbin.com
2. Use `/ai` to switch to AI mode for chatting with Llama 3.1 8B
3. Use `/quit` to return to Termbin mode

## License

MIT
