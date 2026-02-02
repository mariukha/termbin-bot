#!/bin/bash
# Setup script for Google Cloud VM (Ubuntu/Debian)

echo "🚀 Setting up Termbin Bot..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Install system dependencies
sudo apt install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-ukr tesseract-ocr-pol tesseract-ocr-rus tesseract-ocr-deu
sudo apt install -y ffmpeg

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "To run the bot:"
echo "1. Set environment variables:"
echo "   export TERMBIN_BOT_TOKEN='your_telegram_token'"
echo "   export OPENROUTER_API_KEY='your_openrouter_key'"
echo ""
echo "2. Activate venv and run:"
echo "   source venv/bin/activate"
echo "   python3 bot.py"
