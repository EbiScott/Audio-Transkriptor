import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Groq client
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    print("ERROR: GROQ_API_KEY not found in .env file!")
    exit(1)

groq_client = Groq(api_key=groq_api_key)

print("✅ Groq client initialized successfully!")

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message when user starts the bot."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n\n"
        "I'm your **FREE Voice Transcriber Bot**! 🎤\n\n"
        "📝 Send me any voice note (any length!)\n"
        "⚡ I'll transcribe it instantly\n"
        "🌍 Works perfectly with Nigerian accents\n"
        "🆓 Completely FREE to use!\n\n"
        "Just send me a voice message to get started! 🚀",
        parse_mode='Markdown'
    )

# Command: /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information."""
    await update.message.reply_text(
        "📖 **How to Use:**\n\n"
        "1️⃣ Record a voice note in Telegram\n"
        "2️⃣ Send it to me\n"
        "3️⃣ Wait a few seconds\n"
        "4️⃣ Get your transcription!\n\n"
        "💡 **Tips:**\n"
        "• Any length audio is fine!\n"
        "• Works with any accent\n"
        "• Super fast transcription\n"
        "• You can also send audio files!\n\n"
        "Questions? Just send /start to see the intro again!",
        parse_mode='Markdown'
    )

# Handle voice messages
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Transcribe voice messages."""
    
    # Send initial processing message
    processing_msg = await update.message.reply_text(
        "🎧 Got your voice note!\n⏳ Transcribing now..."
    )
    
    try:
        voice = update.message.voice
        duration = voice.duration
        file_size = voice.file_size / 1024 / 1024  # Convert to MB
        
        logger.info(f"Processing voice: {duration}s, {file_size:.2f}MB")
        
        # Download the voice file
        voice_file = await context.bot.get_file(voice.file_id)
        temp_file = f"voice_{update.message.message_id}.ogg"
        await voice_file.download_to_drive(temp_file)
        
        logger.info(f"Downloaded: {temp_file}")
        
        # Update status for longer files
        if duration > 60:
            await processing_msg.edit_text(
                f"🎧 Processing {duration}s of audio...\n"
                "⏳ Hang tight, this is a longer one!"
            )
        
        # Transcribe with Groq Whisper
        logger.info("Sending to Groq for transcription...")
        
        with open(temp_file, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(temp_file, file.read()),
                model="whisper-large-v3",  # Best Whisper model
                language="en",  # English (handles Nigerian English well)
                response_format="text",
                temperature=0.0  # More deterministic transcription
            )
        
        logger.info(f"Transcription complete: {len(transcription)} characters")
        
        # Delete temporary file
        os.remove(temp_file)
        logger.info(f"Cleaned up: {temp_file}")
        
        # Send transcription back to user
        if transcription and transcription.strip():
            # Telegram message limit is 4096 characters
            if len(transcription) <= 4000:
                await processing_msg.edit_text(
                    f"✅ **Transcription:**\n\n{transcription}",
                    parse_mode='Markdown'
                )
            else:
                # For very long transcriptions, split into chunks
                await processing_msg.edit_text(
                    "✅ **Transcription complete!** (Sending in parts...)",
                    parse_mode='Markdown'
                )
                
                # Send in 4000-character chunks
                for i in range(0, len(transcription), 4000):
                    chunk = transcription[i:i + 4000]
                    await update.message.reply_text(chunk)
                
                # Send word count summary
                word_count = len(transcription.split())
                await update.message.reply_text(
                    f"📊 Total: {word_count} words, {len(transcription)} characters"
                )
        else:
            await processing_msg.edit_text(
                "⚠️ Could not transcribe this audio.\n"
                "The recording might be silent or unclear."
            )
    
    except Exception as e:
        logger.error(f"Error processing voice: {e}", exc_info=True)
        await processing_msg.edit_text(
            f"❌ **Error occurred:**\n{str(e)}\n\n"
            "Please try again or send /help",
            parse_mode='Markdown'
        )
        
        # Clean up temp file if it exists
        if 'temp_file' in locals() and os.path.exists(temp_file):
            os.remove(temp_file)

# Handle audio files (MP3, M4A, etc.)
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Transcribe audio files."""
    
    processing_msg = await update.message.reply_text(
        "🎵 Got your audio file!\n⏳ Transcribing..."
    )
    
    try:
        audio = update.message.audio
        duration = audio.duration
        file_size = audio.file_size / 1024 / 1024
        
        logger.info(f"Processing audio file: {duration}s, {file_size:.2f}MB")
        
        # Download audio file
        audio_file = await context.bot.get_file(audio.file_id)
        temp_file = f"audio_{update.message.message_id}.mp3"
        await audio_file.download_to_drive(temp_file)
        
        if duration > 60:
            await processing_msg.edit_text(
                f"🎵 Processing {duration}s audio...\n⏳ Please wait..."
            )
        
        # Transcribe
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
                await processing_msg.edit_text(
                    f"✅ **Transcription:**\n\n{transcription}",
                    parse_mode='Markdown'
                )
            else:
                await processing_msg.edit_text("✅ **Done!** (Sending in parts...)", parse_mode='Markdown')
                for i in range(0, len(transcription), 4000):
                    await update.message.reply_text(transcription[i:i + 4000])
                
                word_count = len(transcription.split())
                await update.message.reply_text(
                    f"📊 Total: {word_count} words"
                )
        else:
            await processing_msg.edit_text("⚠️ Could not transcribe this audio.")
    
    except Exception as e:
        logger.error(f"Error processing audio: {e}", exc_info=True)
        await processing_msg.edit_text(f"❌ **Error:** {str(e)}", parse_mode='Markdown')
        if 'temp_file' in locals() and os.path.exists(temp_file):
            os.remove(temp_file)

def main():
    """Start the bot."""
    
    # Get Telegram bot token
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN not found in .env file!")
        print("Please add it to your .env file.")
        return
    
    # Create the Application
    print("🤖 Initializing bot...")
    application = Application.builder().token(token).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Register message handlers
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    
    # Start the bot
    print("=" * 50)
    print("🎉 BOT IS RUNNING!")
    print("=" * 50)
    print("✅ Ready to transcribe voice notes!")
    print("📱 Go to Telegram and send a voice message to your bot")
    print("🛑 Press Ctrl+C to stop the bot")
    print("=" * 50)
    print()
    
    # Run the bot until Ctrl+C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
