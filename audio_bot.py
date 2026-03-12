import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    print("ERROR: GROQ_API_KEY not found in .env file!")
    exit(1)

groq_client = Groq(api_key=groq_api_key)
print("✅ Groq client initialized successfully!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n\n"
        "I'm your FREE Voice Transcriber Bot! 🎤\n\n"
        "📝 Send me any voice note (any length!)\n"
        "⚡ I'll transcribe it instantly\n"
        "🌍 Works perfectly with Nigerian accents\n"
        "🆓 Completely FREE to use!\n\n"
        "Just send me a voice message to get started! 🚀"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 How to Use:\n\n"
        "1️⃣ Record a voice note in Telegram\n"
        "2️⃣ Send it to me\n"
        "3️⃣ Wait a few seconds\n"
        "4️⃣ Get your transcription!\n\n"
        "💡 Tips:\n"
        "• Any length audio is fine!\n"
        "• Works with any accent\n"
        "• Super fast transcription\n"
        "• You can also send audio files!"
    )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    processing_msg = await update.message.reply_text("🎧 Transcribing...")
    
    try:
        voice = update.message.voice
        duration = voice.duration
        
        logger.info(f"Processing voice: {duration}s")
        
        voice_file = await context.bot.get_file(voice.file_id)
        temp_file = f"voice_{update.message.message_id}.ogg"
        await voice_file.download_to_drive(temp_file)
        
        logger.info("Sending to Groq...")
        
        with open(temp_file, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(temp_file, file.read()),
                model="whisper-large-v3",
                language="en",
                response_format="text",
                temperature=0.0
            )
        
        os.remove(temp_file)
        logger.info("Transcription complete")
        
        if transcription and transcription.strip():
            if len(transcription) <= 4000:
                await processing_msg.edit_text(f"✅ Transcription:\n\n{transcription}")
            else:
                await processing_msg.edit_text("✅ Done! (Sending in parts...)")
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
    processing_msg = await update.message.reply_text("🎵 Transcribing audio...")
    
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

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN not found!")
        return
    
    print("🤖 Initializing bot...")
    
    # Build application with explicit configuration
    application = (
        Application.builder()
        .token(token)
        .concurrent_updates(True)
        .build()
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    
    print("=" * 50)
    print("🎉 BOT IS RUNNING!")
    print("=" * 50)
    print("✅ Ready to transcribe!")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()