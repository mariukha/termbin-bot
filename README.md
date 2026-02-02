# Termbin + AI Telegram Bot

A Telegram bot that combines text sharing via [termbin.com](https://termbin.com) with AI chat, OCR, and voice features.

## Features

- **Termbin Mode** (default): Send any text and get a shareable termbin.com link
- **AI Mode**: Chat with Llama 3.1 8B for coding help and Q&A
- **OCR**: Extract text from photos (multi-language)
- **Voice-to-Text**: Send voice messages to get transcription (Whisper)
- **Text-to-Speech**: `/tts <text>` to generate audio (auto language detection)

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show help message |
| `/ai` | Enter AI mode |
| `/quit` | Exit AI mode, return to Termbin |
| `/tts <text>` | Convert text to speech |

## Local Setup

### 1. Get API Keys

- **Telegram Bot Token**: Get from [@BotFather](https://t.me/BotFather)
- **OpenRouter API Key**: Get from [openrouter.ai](https://openrouter.ai/keys)

### 2. Install Dependencies

```bash
# macOS
brew install tesseract tesseract-lang ffmpeg
pip install -r requirements.txt
```

### 3. Run the Bot

```bash
export TERMBIN_BOT_TOKEN="your_telegram_bot_token"
export OPENROUTER_API_KEY="your_openrouter_api_key"
python3 bot.py
```

## Deploy to Google Cloud VM

### 1. Create VM Instance

- Go to [Google Cloud Console](https://console.cloud.google.com)
- Create a new VM (e2-small or higher recommended)
- Choose Ubuntu 22.04 LTS
- Allow HTTP/HTTPS traffic

### 2. SSH into VM and Clone Repo

```bash
git clone https://github.com/mariukha/termbin-bot.git
cd termbin-bot
```

### 3. Run Setup Script

```bash
chmod +x setup.sh
./setup.sh
```

### 4. Configure and Run

```bash
# Edit service file with your credentials
nano termbin-bot.service
# Replace YOUR_USERNAME, tokens, etc.

# Install as systemd service
sudo cp termbin-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable termbin-bot
sudo systemctl start termbin-bot

# Check status
sudo systemctl status termbin-bot
```

## License

MIT
