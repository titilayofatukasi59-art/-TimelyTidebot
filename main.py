import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    JobQueue
)

# --- Logging Configuration ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    logger.error("❌ TELEGRAM_TOKEN environment variable not set!")
    sys.exit(1)

# --- User Data Storage (In-memory, will reset on restart) ---
user_preferences = {}  # user_id: {"timezone": str, "notifications": bool}

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with welcome message and menu."""
    user = update.effective_user
    welcome_message = (
        f"🌊 Welcome to TimelyTideBot, {user.first_name}!\n\n"
        "I'm your tide and timing assistant. I can help you with:\n"
        "📅 Daily tide predictions\n"
        "⏰ Time-based reminders\n"
        "🌍 Timezone conversions\n\n"
        "Use the buttons below to get started:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🌊 Get Tide Info", callback_data="tide"),
            InlineKeyboardButton("⏰ Set Reminder", callback_data="reminder"),
        ],
        [
            InlineKeyboardButton("🌍 Set Timezone", callback_data="timezone"),
            InlineKeyboardButton("ℹ️ Help", callback_data="help"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "📖 **TimelyTideBot Help**\n\n"
        "**Commands:**\n"
        "/start - Show main menu\n"
        "/help - Show this help\n"
        "/tide - Get tide information\n"
        "/remind - Set a reminder\n"
        "/timezone - Set your timezone\n"
        "/status - Check your settings\n\n"
        "**Features:**\n"
        "• Get tide predictions for your area\n"
        "• Set custom reminders with time zones\n"
        "• Convert times between zones\n"
        "• Daily tide notifications\n\n"
        "For more information, visit our GitHub page."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def tide_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tide command."""
    user_id = update.effective_user.id
    timezone = user_preferences.get(user_id, {}).get("timezone", "UTC")
    
    # Simulate tide data (replace with real API in production)
    current_time = datetime.now().strftime("%H:%M")
    tide_message = (
        f"🌊 **Tide Information**\n"
        f"📍 Timezone: {timezone}\n"
        f"🕐 Current Time: {current_time}\n\n"
        f"**Today's Tides:**\n"
        f"🌅 High Tide: 06:30 AM (2.8m)\n"
        f"🌊 Low Tide: 12:45 PM (0.5m)\n"
        f"🌅 High Tide: 07:15 PM (3.1m)\n"
        f"🌊 Low Tide: 01:20 AM (0.3m)\n\n"
        f"_Note: This is sample data. Connect to a real tide API for accurate predictions._"
    )
    await update.message.reply_text(tide_message, parse_mode='Markdown')

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /remind command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "⏰ Please provide a reminder!\n"
            "Usage: /remind [time] [message]\n"
            "Example: /remind 30 Check the tide"
        )
        return
    
    try:
        # Parse time and message
        time_minutes = int(args[0])
        message = " ".join(args[1:]) if len(args) > 1 else "Time to check the tide!"
        
        # Schedule the reminder
        job_removed = context.job_queue.get_jobs_by_name(str(update.effective_user.id))
        for job in job_removed:
            job.schedule_removal()
        
        job = context.job_queue.run_once(
            send_reminder,
            timedelta(minutes=time_minutes),
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id,
            data=message,
            name=str(update.effective_user.id)
        )
        
        await update.message.reply_text(
            f"✅ Reminder set for {time_minutes} minutes from now!\n"
            f"📝 Message: {message}"
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid time format. Please use a number.\n"
            "Example: /remind 30 Check the tide"
        )

async def timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /timezone command."""
    args = context.args
    if not args:
        current_tz = user_preferences.get(update.effective_user.id, {}).get("timezone", "UTC")
        await update.message.reply_text(
            f"🌍 Current timezone: {current_tz}\n\n"
            "To change your timezone:\n"
            "/timezone UTC\n"
            "/timezone EST\n"
            "/timezone PST\n"
            "/timezone GMT\n\n"
            "Supported timezones: UTC, EST, PST, GMT, CET, IST"
        )
        return
    
    timezone = args[0].upper()
    valid_timezones = ["UTC", "EST", "PST", "GMT", "CET", "IST"]
    
    if timezone not in valid_timezones:
        await update.message.reply_text(
            f"❌ Invalid timezone. Supported: {', '.join(valid_timezones)}"
        )
        return
    
    # Save user preference
    user_id = update.effective_user.id
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    user_preferences[user_id]["timezone"] = timezone
    
    await update.message.reply_text(f"✅ Timezone set to {timezone}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command to show user settings."""
    user_id = update.effective_user.id
    prefs = user_preferences.get(user_id, {})
    
    status_text = (
        f"📊 **Your Status**\n\n"
        f"🆔 User ID: {user_id}\n"
        f"🌍 Timezone: {prefs.get('timezone', 'Not set')}\n"
        f"🔔 Notifications: {'Enabled' if prefs.get('notifications', True) else 'Disabled'}\n"
        f"📅 Joined: {datetime.now().strftime('%Y-%m-%d')}"
    )
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo any non-command messages."""
    text = update.message.text
    await update.message.reply_text(
        f"📢 You said: {text}\n\n"
        "Type /help to see available commands."
    )

# --- Callback Query Handler ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()  # Acknowledge the button press
    
    data = query.data
    
    if data == "tide":
        await tide_command(update, context)
    elif data == "reminder":
        await update.effective_message.reply_text(
            "⏰ To set a reminder, use:\n"
            "/remind [minutes] [message]\n\n"
            "Example: /remind 30 Check the tide"
        )
    elif data == "timezone":
        await timezone_command(update, context)
    elif data == "help":
        await help_command(update, context)
    else:
        await query.edit_message_text("❌ Unknown command!")

# --- Reminder Function ---
async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a reminder to the user."""
    job = context.job
    chat_id = job.chat_id
    message = job.data
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏰ **Reminder!**\n\n{message}\n\n🌊 Don't forget to check the tide!"
    )

# --- Error Handler ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. Please try again later."
        )

# --- Periodic Tide Update ---
async def daily_tide_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send daily tide updates to all users."""
    for user_id, prefs in user_preferences.items():
        if prefs.get("notifications", True):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🌊 **Daily Tide Update**\n\n"
                         "High Tide: 06:30 AM (2.8m)\n"
                         "Low Tide: 12:45 PM (0.5m)\n"
                         "High Tide: 07:15 PM (3.1m)\n\n"
                         "Have a great day! 🏄‍♂️"
                )
            except Exception as e:
                logger.error(f"Failed to send tide update to {user_id}: {e}")

# --- Main Function ---
def main() -> None:
    """Start the bot."""
    try:
        logger.info("🚀 Starting TimelyTideBot...")
        logger.info(f"🤖 Bot username: @TimelyTideBot")
        
        # Create application
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Add command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("tide", tide_command))
        app.add_handler(CommandHandler("remind", remind_command))
        app.add_handler(CommandHandler("timezone", timezone_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        # Add callback handler
        app.add_handler(CallbackQueryHandler(button_callback))
        
        # Add error handler
        app.add_error_handler(error_handler)
        
        # Set up periodic tasks
        job_queue = app.job_queue
        if job_queue:
            # Send daily updates at 8:00 AM
            job_queue.run_daily(
                daily_tide_update,
                time=datetime.strptime("08:00", "%H:%M").time(),
                days=(0, 1, 2, 3, 4, 5, 6)
            )
            logger.info("⏰ Daily tide updates scheduled for 8:00 AM")
        else:
            logger.warning("⚠️ Job queue not available - scheduling disabled")
        
        # Start the bot
        logger.info("✅ Bot is running and ready for messages!")
        app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
