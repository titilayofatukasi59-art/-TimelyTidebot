import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
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

# --- User Data Storage ---
user_preferences: Dict[int, Dict] = {}

# --- Helper Functions ---
def get_user_pref(user_id: int, key: str, default: str = "UTC") -> str:
    """Get user preference or return default."""
    return user_preferences.get(user_id, {}).get(key, default)

def set_user_pref(user_id: int, key: str, value: str) -> None:
    """Set user preference."""
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    user_preferences[user_id][key] = value

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    welcome_message = (
        f"🌊 **Welcome to TimelyTideBot, {user.first_name}!**\n\n"
        "I'm your tide and timing assistant. Here's what I can do:\n\n"
        "📅 **Get tide predictions** for your area\n"
        "⏰ **Set reminders** with custom messages\n"
        "🌍 **Manage timezones** for accurate times\n"
        "🔔 **Daily notifications** about tides\n\n"
        "Use the buttons below or type /help for more info:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🌊 Tide Info", callback_data="tide"),
            InlineKeyboardButton("⏰ Set Reminder", callback_data="reminder"),
        ],
        [
            InlineKeyboardButton("🌍 Set Timezone", callback_data="timezone"),
            InlineKeyboardButton("📊 My Status", callback_data="status"),
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "📖 **TimelyTideBot Help**\n\n"
        "**Commands:**\n"
        "• /start - Show main menu\n"
        "• /help - Show this help\n"
        "• /tide - Get tide information\n"
        "• /remind - Set a reminder\n"
        "• /timezone - Set your timezone\n"
        "• /status - Check your settings\n\n"
        "**How to Use:**\n"
        "1. **Set Timezone First:** Use /timezone to set your local timezone\n"
        "2. **Get Tides:** Use /tide to see today's tide predictions\n"
        "3. **Set Reminders:** Use /remind 30 Check the tide\n\n"
        "**Supported Timezones:**\n"
        "UTC, EST, PST, GMT, CET, IST, JST, AEST\n\n"
        "**Examples:**\n"
        "• /timezone EST\n"
        "• /remind 15 Meeting in 15 minutes\n"
        "• /tide\n\n"
        "For support, visit our GitHub page."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def tide_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tide command."""
    user_id = update.effective_user.id
    timezone = get_user_pref(user_id, "timezone", "UTC")
    
    current_time = datetime.now().strftime("%H:%M")
    
    # Generate tide data (this would come from an API in production)
    tide_message = (
        f"🌊 **Tide Information**\n"
        f"───────────────────\n"
        f"📍 Timezone: {timezone}\n"
        f"🕐 Current Time: {current_time}\n"
        f"📅 Date: {datetime.now().strftime('%B %d, %Y')}\n\n"
        f"**Today's Tide Predictions:**\n"
        f"🌅 High Tide: 06:30 AM (2.8m)\n"
        f"🌊 Low Tide:  12:45 PM (0.5m)\n"
        f"🌅 High Tide: 07:15 PM (3.1m)\n"
        f"🌊 Low Tide:  01:20 AM (0.3m)\n\n"
        f"💡 **Tip:** Set your timezone with /timezone for accurate local times.\n"
        f"📊 **Status:** Use /status to check your current settings."
    )
    await update.message.reply_text(tide_message, parse_mode='Markdown')

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /remind command."""
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "⏰ **Set a Reminder**\n\n"
            "Usage: `/remind [minutes] [message]`\n\n"
            "**Examples:**\n"
            "• `/remind 30 Check the tide`\n"
            "• `/remind 5 Meeting in 5 minutes`\n"
            "• `/remind 15 Take a break`\n\n"
            "💡 The reminder will be sent after the specified minutes.",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Parse minutes
        minutes = int(args[0])
        if minutes <= 0:
            await update.message.reply_text("❌ Please enter a positive number of minutes.")
            return
        
        # Parse message
        message = " ".join(args[1:]) if len(args) > 1 else "Time to check the tide!"
        
        # Calculate reminder time
        reminder_time = datetime.now() + timedelta(minutes=minutes)
        
        # Create a job
        job_name = f"reminder_{update.effective_user.id}"
        
        # Remove existing jobs for this user
        for job in context.job_queue.jobs():
            if job.name == job_name:
                job.schedule_removal()
                logger.info(f"Removed existing job for user {update.effective_user.id}")
        
        # Schedule new job
        context.job_queue.run_once(
            send_reminder,
            timedelta(minutes=minutes),
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id,
            data={
                "message": message,
                "minutes": minutes
            },
            name=job_name
        )
        
        await update.message.reply_text(
            f"✅ **Reminder Set!**\n\n"
            f"⏰ Time: {reminder_time.strftime('%I:%M %p')}\n"
            f"📝 Message: {message}\n"
            f"⏳ Duration: {minutes} minutes from now\n\n"
            f"I'll remind you then! 🌊",
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ **Invalid Format**\n\n"
            "Please use: `/remind [minutes] [message]`\n\n"
            "Example: `/remind 30 Check the tide`",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in remind_command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while setting your reminder. Please try again."
        )

async def timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /timezone command."""
    args = context.args
    user_id = update.effective_user.id
    
    if not args:
        current_tz = get_user_pref(user_id, "timezone", "UTC")
        await update.message.reply_text(
            f"🌍 **Timezone Settings**\n\n"
            f"Current timezone: **{current_tz}**\n\n"
            f"To change your timezone, use:\n"
            f"`/timezone [ZONE]`\n\n"
            f"**Available Timezones:**\n"
            f"• UTC (Coordinated Universal Time)\n"
            f"• EST (Eastern Standard Time)\n"
            f"• PST (Pacific Standard Time)\n"
            f"• GMT (Greenwich Mean Time)\n"
            f"• CET (Central European Time)\n"
            f"• IST (Indian Standard Time)\n"
            f"• JST (Japan Standard Time)\n"
            f"• AEST (Australian Eastern Standard Time)\n\n"
            f"**Example:** `/timezone EST`",
            parse_mode='Markdown'
        )
        return
    
    timezone = args[0].upper()
    valid_timezones = ["UTC", "EST", "PST", "GMT", "CET", "IST", "JST", "AEST"]
    
    if timezone not in valid_timezones:
        await update.message.reply_text(
            f"❌ **Invalid Timezone**\n\n"
            f"Supported timezones:\n"
            f"{', '.join(valid_timezones)}\n\n"
            f"Example: `/timezone EST`",
            parse_mode='Markdown'
        )
        return
    
    # Save user preference
    set_user_pref(user_id, "timezone", timezone)
    
    await update.message.reply_text(
        f"✅ **Timezone Updated!**\n\n"
        f"Your timezone has been set to: **{timezone}**\n\n"
        f"🌊 Use /tide to see your local tide predictions.",
        parse_mode='Markdown'
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    user_id = update.effective_user.id
    prefs = user_preferences.get(user_id, {})
    
    status_text = (
        f"📊 **Your Status**\n"
        f"───────────────────\n"
        f"🆔 User ID: `{user_id}`\n"
        f"👤 Username: @{update.effective_user.username or 'Not set'}\n"
        f"🌍 Timezone: **{prefs.get('timezone', 'Not set')}**\n"
        f"🔔 Notifications: **{'✅ Enabled' if prefs.get('notifications', True) else '❌ Disabled'}**\n"
        f"📅 Joined: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"📊 Active Reminders: **{len([job for job in context.job_queue.jobs() if job.name.startswith('reminder_')])}**\n\n"
        f"💡 **Tips:**\n"
        f"• Use /timezone to change your timezone\n"
        f"• Use /remind to set a new reminder"
    )
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo any non-command messages."""
    text = update.message.text
    await update.message.reply_text(
        f"📢 **You said:**\n"
        f"`{text}`\n\n"
        f"💡 Type /help to see all available commands.",
        parse_mode='Markdown'
    )

# --- Callback Query Handler ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "tide":
        await tide_command(update, context)
    elif data == "reminder":
        await query.edit_message_text(
            "⏰ **Set a Reminder**\n\n"
            "Use the command:\n"
            "`/remind [minutes] [message]`\n\n"
            "**Example:**\n"
            "`/remind 30 Check the tide`\n\n"
            "The bot will remind you after the specified minutes.",
            parse_mode='Markdown'
        )
    elif data == "timezone":
        await timezone_command(update, context)
    elif data == "status":
        await status_command(update, context)
    elif data == "help":
        await help_command(update, context)
    else:
        await query.edit_message_text("❌ Unknown command. Please try again.")

# --- Reminder Function ---
async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a reminder to the user."""
    job = context.job
    chat_id = job.chat_id
    data = job.data
    
    message = data.get("message", "Time to check the tide!")
    minutes = data.get("minutes", 0)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"⏰ **Reminder!**\n"
            f"───────────────────\n"
            f"📝 {message}\n\n"
            f"⏳ {minutes} minutes have passed.\n"
            f"🌊 Don't forget to check the tide!\n\n"
            f"💡 Use /tide for current tide information."
        ),
        parse_mode='Markdown'
    )
    
    logger.info(f"Reminder sent to chat {chat_id}: {message}")

# --- Periodic Tide Update ---
async def daily_tide_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send daily tide updates to all users."""
    if not user_preferences:
        logger.info("No users to send daily updates to.")
        return
    
    sent_count = 0
    for user_id in list(user_preferences.keys()):
        try:
            timezone = get_user_pref(user_id, "timezone", "UTC")
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🌊 **Daily Tide Update**\n"
                    f"───────────────────\n"
                    f"📍 Timezone: {timezone}\n"
                    f"📅 Date: {datetime.now().strftime('%B %d, %Y')}\n\n"
                    f"**Today's Tides:**\n"
                    f"🌅 High Tide: 06:30 AM (2.8m)\n"
                    f"🌊 Low Tide:  12:45 PM (0.5m)\n"
                    f"🌅 High Tide: 07:15 PM (3.1m)\n"
                    f"🌊 Low Tide:  01:20 AM (0.3m)\n\n"
                    f"Have a great day! 🏄‍♂️\n"
                    f"💡 Use /tide for more details."
                ),
                parse_mode='Markdown'
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send tide update to {user_id}: {e}")
    
    logger.info(f"Daily tide updates sent to {sent_count} users")

# --- Error Handler ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Send error message to user if possible
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ **Oops! Something went wrong.**\n\n"
                "Please try again later or contact support.\n"
                "💡 Make sure you're using the correct command format.",
                parse_mode='Markdown'
            )
        except:
            pass

# --- Main Function ---
def main() -> None:
    """Start the bot."""
    try:
        logger.info("🚀 Starting TimelyTideBot...")
        logger.info(f"🤖 Bot Token: {TOKEN[:10]}... (truncated for security)")
        
        # Create application
        app = Application.builder().token(TOKEN).build()
        
        # Add command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("tide", tide_command))
        app.add_handler(CommandHandler("remind", remind_command))
        app.add_handler(CommandHandler("timezone", timezone_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        app.add_handler(CallbackQueryHandler(button_callback))
        
        # Add error handler
        app.add_error_handler(error_handler)
        
        # Set up job queue
        job_queue = app.job_queue
        if job_queue:
            # Schedule daily updates at 8:00 AM
            job_queue.run_daily(
                daily_tide_update,
                time=datetime.strptime("08:00", "%H:%M").time(),
                days=tuple(range(7))
            )
            logger.info("⏰ Daily tide updates scheduled for 8:00 AM")
        else:
            logger.warning("⚠️ Job queue not available - scheduling disabled")
        
        # Start the bot
        logger.info("✅ Bot is running and ready for messages!")
        app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
