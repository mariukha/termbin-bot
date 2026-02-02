import os
import socket
import asyncio
import tempfile
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
import pytesseract
from PIL import Image
import whisper
from gtts import gTTS

# Get tokens from environment variables
BOT_TOKEN = os.getenv("TERMBIN_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Initialize OpenRouter client (uses OpenAI-compatible API)
openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
) if OPENROUTER_API_KEY else None

# Store user modes and chat histories (in-memory)
user_modes = {}  # user_id -> "ai" or "termbin"
ai_chats = {}    # user_id -> list of messages

# OpenRouter model - Llama 3.1 8B is very cheap and good
AI_MODEL = "meta-llama/llama-3.1-8b-instruct"  # ~$0.00006/1k tokens

# Whisper model for voice recognition (loaded lazily)
whisper_model = None

def get_whisper_model():
    """Lazy load whisper model to save memory."""
    global whisper_model
    if whisper_model is None:
        whisper_model = whisper.load_model("base")  # Options: tiny, base, small, medium, large
    return whisper_model


def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio file to text using Whisper."""
    try:
        model = get_whisper_model()
        result = model.transcribe(audio_path)
        return result["text"].strip()
    except Exception as e:
        return f"Transcription Error: {e}"


def text_to_speech(text: str, output_path: str) -> bool:
    """Convert text to speech and save as audio file."""
    try:
        tts = gTTS(text=text, lang='en')  # Auto-detect doesn't work well, default to English
        tts.save(output_path)
        return True
    except Exception as e:
        return False


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


def extract_text_from_image(image_path: str) -> str:
    """Extract text from image using OCR with preprocessing for better quality."""
    try:
        from PIL import ImageEnhance, ImageFilter, ImageOps
        
        image = Image.open(image_path)
        
        # Convert to RGB first if needed (handles RGBA, etc.)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Preprocessing for better OCR quality
        # 1. Scale up small images first
        width, height = image.size
        if width < 1500:
            scale = 1500 / width
            image = image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
        
        # 2. Convert to grayscale
        gray = image.convert('L')
        
        # 3. Auto-contrast to normalize the image
        gray = ImageOps.autocontrast(gray)
        
        # 4. Increase sharpness
        enhancer = ImageEnhance.Sharpness(gray)
        gray = enhancer.enhance(2.0)
        
        # 5. Apply threshold to create binary image (black text on white background)
        threshold = 140
        binary = gray.point(lambda x: 255 if x > threshold else 0, mode='1')
        binary = binary.convert('L')  # Convert back to grayscale for tesseract
        
        # OCR with multiple languages
        # --psm 6: Assume a single uniform block of text
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(
            binary, 
            lang='eng+ukr+pol+rus+deu',
            config=custom_config
        )
        
        # If result is poor, try with original grayscale (different PSM)
        if len(text.strip()) < 20:
            custom_config = r'--oem 3 --psm 3'
            text = pytesseract.image_to_string(
                gray, 
                lang='eng+ukr+pol+rus+deu',
                config=custom_config
            )
        
        return text.strip() if text.strip() else "No text found in image."
    except Exception as e:
        return f"OCR Error: {e}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /start command."""
    user_id = update.effective_user.id
    user_modes[user_id] = "termbin"  # Default mode
    
    await update.message.reply_text(
        "👋 Hi! I'm a bot for termbin, AI, OCR, and voice.\n\n"
        "📝 *Termbin Mode* (default):\n"
        "• Send text → save to termbin.com\n"
        "• Send photo → extract text (OCR)\n"
        "• Send voice → transcribe to text\n\n"
        "🤖 *AI Mode* (Llama 3.1 8B):\n"
        "/ai — enter AI mode\n"
        "/quit — exit AI mode\n\n"
        "🔊 *Voice:*\n"
        "/tts <text> — text to speech\n\n"
        "You're currently in Termbin mode.",
        parse_mode="Markdown"
    )


async def ai_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /ai command - enters AI mode."""
    user_id = update.effective_user.id
    user_modes[user_id] = "ai"
    
    # Start new chat session for this user
    ai_chats[user_id] = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant. When writing code, always explain what it does. Write clean, high-quality code at a senior developer level."
        }
    ]
    
    await update.message.reply_text(
        "🤖 *AI Mode activated!*\n\n"
        "Model: Llama 3.1 8B\n\n"
        "You can now:\n"
        "• Ask questions\n"
        "• Request code\n"
        "• Send photos (OCR + AI analysis)\n\n"
        "Use /quit to return to termbin.",
        parse_mode="Markdown"
    )


async def quit_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /quit command - exits AI mode."""
    user_id = update.effective_user.id
    user_modes[user_id] = "termbin"
    
    # Clear chat history
    if user_id in ai_chats:
        del ai_chats[user_id]
    
    await update.message.reply_text(
        "📝 *Termbin Mode activated!*\n\n"
        "Your messages will now be saved to termbin.com",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for text messages - routes to AI or Termbin based on mode."""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Get user mode (default to termbin)
    mode = user_modes.get(user_id, "termbin")
    
    if mode == "ai":
        await handle_ai_message(update, context, text, user_id)
    else:
        await handle_termbin_message(update, context, text)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for photo messages - extracts text using OCR."""
    user_id = update.effective_user.id
    mode = user_modes.get(user_id, "termbin")
    
    processing_msg = await update.message.reply_text("🔍 Extracting text from image...")
    
    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Download to temp file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            tmp_path = tmp.name
        
        # Extract text
        loop = asyncio.get_event_loop()
        extracted_text = await loop.run_in_executor(None, extract_text_from_image, tmp_path)
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        if mode == "ai" and openrouter_client and extracted_text != "No text found in image.":
            # In AI mode, send extracted text to AI for analysis
            await processing_msg.edit_text("🤔 Analyzing extracted text...")
            
            # Get caption if any
            caption = update.message.caption or "Analyze this text from the image"
            
            prompt = f"Image text (OCR):\n```\n{extracted_text}\n```\n\nUser request: {caption}"
            
            if user_id not in ai_chats:
                ai_chats[user_id] = [
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant. When writing code, always explain what it does."
                    }
                ]
            
            ai_chats[user_id].append({"role": "user", "content": prompt})
            
            response = await loop.run_in_executor(
                None,
                lambda: openrouter_client.chat.completions.create(
                    model=AI_MODEL,
                    messages=ai_chats[user_id],
                    temperature=0.7,
                    max_tokens=4096
                )
            )
            
            reply_text = response.choices[0].message.content
            ai_chats[user_id].append({"role": "assistant", "content": reply_text})
            
            # Keep history limited
            if len(ai_chats[user_id]) > 21:
                ai_chats[user_id] = [ai_chats[user_id][0]] + ai_chats[user_id][-20:]
            
            try:
                await processing_msg.edit_text(reply_text, parse_mode="Markdown")
            except:
                await processing_msg.edit_text(reply_text)
        else:
            # Just show extracted text
            if len(extracted_text) <= 4000:
                await processing_msg.edit_text(f"📝 *Extracted text:*\n\n{extracted_text}", parse_mode="Markdown")
            else:
                # Upload to termbin if too long
                link = await loop.run_in_executor(None, send_to_termbin, extracted_text)
                if link.startswith("http"):
                    await processing_msg.edit_text(
                        f"📝 Text too long, uploaded to termbin:\n\n🔗 {link}\n\n"
                        f"Preview:\n{extracted_text[:500]}..."
                    )
                else:
                    await processing_msg.edit_text(f"📝 Extracted text:\n\n{extracted_text[:4000]}...")
                    
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error: {e}")


async def handle_ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, user_id: int) -> None:
    """Handle message in AI mode."""
    if not openrouter_client:
        await update.message.reply_text("❌ OPENROUTER_API_KEY not configured!")
        return
    
    processing_msg = await update.message.reply_text("🤔 Thinking...")
    
    try:
        # Get or create chat session
        if user_id not in ai_chats:
            ai_chats[user_id] = [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant. When writing code, always explain what it does. Write clean, high-quality code at a senior developer level."
                }
            ]
        
        # Add user message to history
        ai_chats[user_id].append({"role": "user", "content": text})
        
        # Send to OpenRouter
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: openrouter_client.chat.completions.create(
                model=AI_MODEL,
                messages=ai_chats[user_id],
                temperature=0.7,
                max_tokens=4096
            )
        )
        
        reply_text = response.choices[0].message.content
        
        # Add assistant response to history
        ai_chats[user_id].append({"role": "assistant", "content": reply_text})
        
        # Keep only last 20 messages to avoid token limits
        if len(ai_chats[user_id]) > 21:  # 1 system + 20 messages
            ai_chats[user_id] = [ai_chats[user_id][0]] + ai_chats[user_id][-20:]
        
        # Telegram has 4096 char limit, split if needed
        if len(reply_text) <= 4096:
            try:
                await processing_msg.edit_text(reply_text, parse_mode="Markdown")
            except:
                await processing_msg.edit_text(reply_text)
        else:
            # Delete processing message and send in chunks
            await processing_msg.delete()
            chunks = [reply_text[i:i+4096] for i in range(0, len(reply_text), 4096)]
            for chunk in chunks:
                try:
                    await update.message.reply_text(chunk, parse_mode="Markdown")
                except:
                    await update.message.reply_text(chunk)
                
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error: {e}")


async def handle_termbin_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Handle message in Termbin mode."""
    processing_msg = await update.message.reply_text("⏳ Uploading to termbin.com...")
    
    loop = asyncio.get_event_loop()
    link = await loop.run_in_executor(None, send_to_termbin, text)
    
    if link.startswith("http"):
        await processing_msg.edit_text(f"✅ Done!\n\n🔗 {link}")
    else:
        await processing_msg.edit_text(f"❌ {link}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for voice messages - transcribes to text."""
    user_id = update.effective_user.id
    mode = user_modes.get(user_id, "termbin")
    
    processing_msg = await update.message.reply_text("🎤 Transcribing voice...")
    
    try:
        # Get voice file
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        
        # Download to temp file
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            tmp_path = tmp.name
        
        # Transcribe
        loop = asyncio.get_event_loop()
        transcribed_text = await loop.run_in_executor(None, transcribe_audio, tmp_path)
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        if mode == "ai" and openrouter_client:
            # In AI mode, send transcribed text to AI
            await processing_msg.edit_text(f"🎤 You said: {transcribed_text[:100]}...\n\n🤔 Thinking...")
            await handle_ai_message(update, context, transcribed_text, user_id)
            await processing_msg.delete()
        else:
            # Just show transcribed text
            if len(transcribed_text) <= 4000:
                await processing_msg.edit_text(f"🎤 *Transcribed text:*\n\n{transcribed_text}", parse_mode="Markdown")
            else:
                link = await loop.run_in_executor(None, send_to_termbin, transcribed_text)
                if link.startswith("http"):
                    await processing_msg.edit_text(f"🎤 Text too long, uploaded to termbin:\n\n🔗 {link}")
                else:
                    await processing_msg.edit_text(f"🎤 Transcribed text:\n\n{transcribed_text[:4000]}...")
                    
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error: {e}")


async def tts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /tts command - converts text to speech."""
    if not context.args:
        await update.message.reply_text("Usage: /tts <text to speak>")
        return
    
    text = " ".join(context.args)
    processing_msg = await update.message.reply_text("🔊 Generating audio...")
    
    try:
        loop = asyncio.get_event_loop()
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        
        success = await loop.run_in_executor(None, text_to_speech, text, tmp_path)
        
        if success:
            await processing_msg.delete()
            with open(tmp_path, 'rb') as audio:
                await update.message.reply_voice(audio)
        else:
            await processing_msg.edit_text("❌ Failed to generate audio")
        
        os.unlink(tmp_path)
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error: {e}")


def main() -> None:
    """Start the bot."""
    if not BOT_TOKEN:
        print("❌ Error: TERMBIN_BOT_TOKEN not set!")
        return
    
    if not OPENROUTER_API_KEY:
        print("⚠️ Warning: OPENROUTER_API_KEY not set! AI mode will not work.")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ai", ai_mode))
    application.add_handler(CommandHandler("quit", quit_mode))
    application.add_handler(CommandHandler("tts", tts_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot is running! Press Ctrl+C to stop.")
    print(f"   AI Mode: {'✅ Enabled' if OPENROUTER_API_KEY else '❌ Disabled (no API key)'}")
    print("   OCR: ✅ Enabled")
    print("   Voice: ✅ Enabled (Whisper + gTTS)")
    application.run_polling()


if __name__ == "__main__":
    main()
