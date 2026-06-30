import os
import logging
import asyncio
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment variable
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set!")

# Store user subscriptions in memory (for demo - use database in production)
user_subscriptions = {}

# Store scheduled messages (for demo)
scheduled_messages = []

# Bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    user = update.effective_user
    welcome_text = f"""
🌊 Hello {user.first_name}! Welcome to TimelyTide Bot!

I'm here to help you stay updated with:
• ⏰ Timely reminders
• 📊 Daily tide information
• 🔔 Custom notifications
• 📅 Scheduled updates

Use /help to see all available commands.
"""
    keyboard = [
        [InlineKeyboardButton("Subscribe for Updates", callback_data='subscribe')],
        [InlineKeyboardButton("View My Subscriptions", callback_data='view_subs')],
        [InlineKeyboardButton("Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when /help is issued."""
    help_text = """
📚 *Available Commands:*

/start - Start the bot and see welcome message
/help - Show this help message
/subscribe - Subscribe to daily tide updates
/unsubscribe - Unsubscribe from updates
/mysubs - View your current subscriptions
/settime - Set your preferred notification time (format: HH:MM)
/status - Check bot status

*How to Use:*
1. Subscribe to get daily tide updates
2. Set your preferred time for notifications
3. Receive timely updates every day!

For support, contact: @your_support_handle
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe user to daily updates."""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    if user_id not in user_subscriptions:
        user_subscriptions[user_id] = {
            'username': username,
            'subscribed_at': datetime.now().isoformat(),
            'preference_time': "09:00",  # Default time
            'active': True
        }
        await update.message.reply_text(
            "✅ You have been successfully subscribed to daily tide updates!\n"
            "You'll receive updates at 9:00 AM daily.\n"
            "Use /settime to change the time."
        )
        logger.info(f"User {user_id} ({username}) subscribed")
    else:
        await update.message.reply_text(
            "ℹ️ You are already subscribed!\n"
            "Use /unsubscribe to stop receiving updates."
        )

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unsubscribe user from updates."""
    user_id = update.effective_user.id
    
    if user_id in user_subscriptions:
        user_subscriptions[user_id]['active'] = False
        await update.message.reply_text(
            "❌ You have been unsubscribed from updates.\n"
            "Use /subscribe to resubscribe anytime."
        )
        logger.info(f"User {user_id} unsubscribed")
    else:
        await update.message.reply_text(
            "ℹ️ You are not currently subscribed.\n"
            "Use /subscribe to start receiving updates!"
        )

async def my_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's current subscriptions."""
    user_id = update.effective_user.id
    
    if user_id in user_subscriptions:
        sub_data = user_subscriptions[user_id]
        status = "Active ✅" if sub_data['active'] else "Inactive ❌"
        text = f"""
📋 *Your Subscription Details:*

Status: {status}
Subscribed: {sub_data['subscribed_at']}
Preference Time: {sub_data['preference_time']}
Username: @{sub_data['username']}

Use /unsubscribe to stop updates
Use /settime to change notification time
"""
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(
            "📭 You don't have any active subscriptions.\n"
            "Use /subscribe to get started!"
        )

async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set preferred notification time."""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "⏰ Please provide a time in HH:MM format.\n"
            "Example: /settime 14:30\n\n"
            "Current time: " + (user_subscriptions.get(user_id, {}).get('preference_time', '09:00'))
        )
        return
    
    try:
        time_str = context.args[0]
        # Validate time format
        datetime.strptime(time_str, "%H:%M")
        
        if user_id not in user_subscriptions:
            # Auto-subscribe if not subscribed
            user_subscriptions[user_id] = {
                'username': update.effective_user.username or "Unknown",
                'subscribed_at': datetime.now().isoformat(),
                'preference_time': time_str,
                'active': True
            }
        else:
            user_subscriptions[user_id]['preference_time'] = time_str
        
        await update.message.reply_text(
            f"✅ Notification time updated to {time_str}!\n"
            "You'll receive updates at this time daily."
        )
        logger.info(f"User {user_id} set time to {time_str}")
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid time format!\n"
            "Please use HH:MM format (e.g., 14:30)"
        )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bot status."""
    status_text = f"""
🤖 *Bot Status*

Bot: @TimelyTidebot
Status: 🟢 Online
Total Subscribers: {len(user_subscriptions)}
Active Users: {len([u for u in user_subscriptions.values() if u.get('active', True)])}
Uptime: Running continuously

*Features:*
✅ 24/7 Operation
✅ Scheduled Updates
✅ Custom Time Settings
✅ Real-time Responses

_Use /help for commands_
"""
    await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'subscribe':
        await subscribe(update, context)
        await query.edit_message_text("✅ You've been subscribed!")
    elif query.data == 'view_subs':
        await my_subscriptions(update, context)
    elif query.data == 'help':
        await help_command(update, context)
    elif query.data == 'settime':
        await set_time(update, context)

async def send_daily_updates(context: ContextTypes.DEFAULT_TYPE):
    """Send daily tide updates to all active subscribers."""
    logger.info("Sending daily updates...")
    current_time = datetime.now().strftime("%H:%M")
    
    # Generate tide information (mock data - replace with actual tide API)
    tide_info = generate_tide_info()
    
    for user_id, data in user_subscriptions.items():
        if data.get('active', True):
            try:
                # Check if current time matches user's preference
                user_time = data.get('preference_time', '09:00')
                if current_time == user_time:
                    message = f"""
🌊 *Daily Tide Update* 🌊

📅 Date: {datetime.now().strftime('%B %d, %Y')}
⏰ Time: {current_time}

{tide_info}

ℹ️ _Stay informed about the tides!_
_To unsubscribe: /unsubscribe_
"""
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    logger.info(f"Sent update to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")

def generate_tide_info():
    """Generate mock tide information. Replace with actual API call."""
    import random
    tides = [
        "🔵 High Tide: 1.2m\n⚪ Low Tide: 0.3m\n🌊 Wave Height: 0.5m\n💨 Wind: 15 km/h",
        "🔵 High Tide: 1.5m\n⚪ Low Tide: 0.2m\n🌊 Wave Height: 0.8m\n💨 Wind: 20 km/h",
        "🔵 High Tide: 0.8m\n⚪ Low Tide: 0.1m\n🌊 Wave Height: 0.3m\n💨 Wind: 10 km/h",
        "🔵 High Tide: 2.0m\n⚪ Low Tide: 0.4m\n🌊 Wave Height: 1.2m\n💨 Wind: 25 km/h",
        "🔵 High Tide: 1.8m\n⚪ Low Tide: 0.3m\n🌊 Wave Height: 0.9m\n💨 Wind: 18 km/h"
    ]
    return random.choice(tides)

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands."""
    await update.message.reply_text(
        "❓ Unknown command. Please use /help to see all available commands."
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ An error occurred. Please try again later."
            )
    except:
        pass

def main():
    """Start the bot."""
    logger.info("Starting TimelyTide Bot...")
    
    # Create application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("mysubs", my_subscriptions))
    application.add_handler(CommandHandler("settime", set_time))
    application.add_handler(CommandHandler("status", status))
    
    # Add callback handler for inline buttons
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Add fallback handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Schedule daily updates (runs every minute to check time)
    job_queue = application.job_queue
    if job_queue:
        # Run every minute to check for scheduled times
        job_queue.run_repeating(send_daily_updates, interval=60.0, first=10)
        logger.info("Scheduled job created")
    
    # Start the bot using polling
    logger.info("Bot is ready and running! Press Ctrl+C to stop.")
    
    # Run the bot (will block until stopped)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
