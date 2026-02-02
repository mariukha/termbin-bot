import os
import socket
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Get token from environment variable
BOT_TOKEN = os.getenv("TERMBIN_BOT_TOKEN")


def send_to_termbin(text: str) -> str:
    """Sends text to termbin.com and returns the link."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("termbin.com", 9999))
            sock.sendall(text.encode("utf-8"))
            sock.shutdown(socket.SHUT_WR)
            response = sock.recv(1024).decode("utf-8").strip()
            return response
    except Exception as e:
        return f"Error: {e}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /start command."""
    await update.message.reply_text(
        "👋 Hi! Send me any text message, "
        "and I'll save it to termbin.com and give you the link."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for text messages."""
    text = update.message.text
    
    # Send processing message to user
    processing_msg = await update.message.reply_text("⏳ Uploading to termbin.com...")
    
    # Send to termbin in background thread
    loop = asyncio.get_event_loop()
    link = await loop.run_in_executor(None, send_to_termbin, text)
    
    # Edit message with result
    if link.startswith("http"):
        await processing_msg.edit_text(f"✅ Done!\n\n🔗 {link}")
    else:
        await processing_msg.edit_text(f"❌ {link}")


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot is running! Press Ctrl+C to stop.")
    application.run_polling()


if __name__ == "__main__":
    main()
