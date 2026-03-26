import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from flask import Flask, request
import asyncio

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # We'll set this later

if not TELEGRAM_BOT_TOKEN or not GROQ_API_KEY:
    logger.error("Missing required environment variables!")
    exit(1)

# Initialize Groq
groq_client = Groq(api_key=GROQ_API_KEY)
logger.info("✅ Groq client initialized!")

# Initialize Flask app (for receiving webhooks)
app = Flask(__name__)

# Initialize Telegram Application
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n\n"
        "I'm your FREE Voice Transcriber Bot! 🎤\n\n"
        "📝 Send me any voice note\n"
        "⚡ I'll transcribe it instantly\n"
        "🌍 Works with Nigerian accents\n\n"
        "Send a voice message to start! 🚀"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 How to Use:\n\n"
        "1️⃣ Record a voice note\n"
        "2️⃣ Send it to me\n"
        "3️⃣ Get transcription!\n\n"
        "Works with any length audio!"
    )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    processing_msg = await update.message.reply_text("🎧 Transcribing...")
    
    try:
        voice = update.message.voice
        duration = voice.duration
        
        logger.info(f"Processing {duration}s voice note")
        
        # Download voice file
        voice_file = await context.bot.get_file(voice.file_id)
        temp_file = f"voice_{update.message.message_id}.ogg"
        await voice_file.download_to_drive(temp_file)
        
        # Transcribe with Groq
        with open(temp_file, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(temp_file, file.read()),
                model="whisper-large-v3",
                language="en",
                response_format="text",
                temperature=0.0
            )
        
        # Clean up
        os.remove(temp_file)
        logger.info("Transcription complete")
        
        # Send result
        if transcription and transcription.strip():
            if len(transcription) <= 4000:
                await processing_msg.edit_text(f"✅ Transcription:\n\n{transcription}")
            else:
                await processing_msg.edit_text("✅ Done! (Parts below)")
                for i in range(0, len(transcription), 4000):
                    await update.message.reply_text(transcription[i:i + 4000])
        else:
            await processing_msg.edit_text("⚠️ No speech detected")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        await processing_msg.edit_text(f"❌ Error: {str(e)}")
        if 'temp_file' in locals() and os.path.exists(temp_file):
            os.remove(temp_file)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    processing_msg = await update.message.reply_text("🎵 Transcribing...")
    
    try:
        audio = update.message.audio
        audio_file = await context.bot.get_file(audio.file_id)
        temp_file = f"audio_{update.message.message_id}.mp3"
        await audio_file.download_to_drive(temp_file)
        
        with open(temp_file, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(temp_file, file.read()),
                model="whisper-large-v3",
                language="en",
                response_format="text",
                temperature=0.0
            )
        
        os.remove(temp_file)
        
        if transcription and transcription.strip():
            if len(transcription) <= 4000:
                await processing_msg.edit_text(f"✅ Transcription:\n\n{transcription}")
            else:
                await processing_msg.edit_text("✅ Done!")
                for i in range(0, len(transcription), 4000):
                    await update.message.reply_text(transcription[i:i + 4000])
        else:
            await processing_msg.edit_text("⚠️ No speech detected")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        await processing_msg.edit_text(f"❌ Error: {str(e)}")
        if 'temp_file' in locals() and os.path.exists(temp_file):
            os.remove(temp_file)

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.VOICE, handle_voice))
application.add_handler(MessageHandler(filters.AUDIO, handle_audio))

# Flask webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates via webhook"""
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.run(application.process_update(update))
        return 'ok'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'error', 500

@app.route('/')
def index():
    """Health check endpoint"""
    return 'Bot is running! 🤖'

@app.route('/set_webhook')
def set_webhook():
    """Manually set webhook (for testing)"""
    if not WEBHOOK_URL:
        return 'WEBHOOK_URL not set', 400
    
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        asyncio.run(application.bot.set_webhook(webhook_url))
        return f'Webhook set to {webhook_url}'
    except Exception as e:
        return f'Error setting webhook: {e}', 500

if __name__ == '__main__':
    logger.info("🤖 Starting bot with webhooks...")
    
    # Set webhook if WEBHOOK_URL is provided
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        asyncio.run(application.bot.set_webhook(webhook_url))
        logger.info(f"✅ Webhook set to: {webhook_url}")
    
    # Start Flask server
    port = int(os.getenv('PORT', 10000))
    logger.info(f"✅ Server starting on port {port}")
    app.run(host='0.0.0.0', port=port)
