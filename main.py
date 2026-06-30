import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- Configuration ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set!")

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    await update.message.reply_text(
        "👋 Hello! I'm TimelyTideBot, your helpful assistant.\n"
        "Send me any message and I'll echo it back!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    await update.message.reply_text(
        "📖 Here's how to use me:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "Any other text - I'll echo it back!"
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo the user's message."""
    await update.message.reply_text(f"📢 You said: {update.message.text}")

# --- Main Function ---
def main():
    """Start the bot using long polling."""
    print("🚀 Starting bot with long polling...")
    
    # Build the application
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Start long polling
    print("✅ Bot is running! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
