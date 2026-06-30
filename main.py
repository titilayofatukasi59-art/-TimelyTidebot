import os
import logging
import sys
from datetime import datetime
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
BOT_NAME = os.environ.get('BOT_NAME', 'TimelyTidebot')

# Log startup information
logger.info("=" * 60)
logger.info(f"Starting {BOT_NAME}...")
logger.info(f"Token Status: {'✅ Set' if TOKEN else '❌ Missing'}")
logger.info("=" * 60)

# If token is missing, exit gracefully
if not TOKEN:
    logger.error("❌ TELEGRAM_TOKEN environment variable not set!")
    logger.error("Please add TELEGRAM_TOKEN to your Railway environment variables")
    logger.error("Go to: Railway Dashboard → Your Service → Variables tab")
    logger.error("Add variable: TELEGRAM_TOKEN = your_bot_token")
    sys.exit(1)

# Store user subscriptions in memory
user_subscriptions = {}

# Bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    user = update.effective_user
    welcome_text = f"""
🌊 Hello {user.first_name}! Welcome to {BOT_NAME}!

I'm here to help you stay updated with:
• ⏰ Timely reminders
• 📊 Daily tide information
• 🔔 Custom notifications
• 📅 Scheduled updates

Use /help to see all available commands.
"""
    keyboard = [
        [InlineKeyboardButton("📋 Subscribe for Updates", callback_data='subscribe')],
        [InlineKeyboardButton("👤 View My Subscriptions", callback_data='view_subs')],
        [InlineKeyboardButton("❓ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when /help is issued."""
    help_text = f"""
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

*Tips:*
• You can set any time using 24-hour format
• You'll receive updates at your preferred time
• You can unsubscribe anytime

For support, contact: @your_support_handle
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe user to daily updates."""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    first_name = update.effective_user.first_name or "User"
    
    if user_id not in user_subscriptions:
        user_subscriptions[user_id] = {
            'username': username,
            'first_name': first_name,
            'subscribed_at': datetime.now().isoformat(),
            'preference_time': "09:00",
            'active': True
        }
        await update.message.reply_text(
            f"✅ You have been successfully subscribed to daily tide updates!\n"
            f"⏰ You'll receive updates at 9:00 AM daily.\n"
            f"🔧 Use /settime to change the time.\n"
            f"📋 Use /mysubs to view your subscription."
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
        if user_subscriptions[user_id].get('active', True):
            user_subscriptions[user_id]['active'] = False
            await update.message.reply_text(
                "❌ You have been unsubscribed from updates.\n"
                "Use /subscribe to resubscribe anytime."
            )
            logger.info(f"User {user_id} unsubscribed")
        else:
            await update.message.reply_text(
                "ℹ️ You are already unsubscribed.\n"
                "Use /subscribe to start receiving updates again!"
            )
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
        status = "Active ✅" if sub_data.get('active', True) else "Inactive ❌"
        text = f"""
📋 *Your Subscription Details*

━━━━━━━━━━━━━━━━━━━━━
👤 *User:* @{sub_data['username']}
📊 *Status:* {status}
📅 *Subscribed:* {sub_data['subscribed_at']}
⏰ *Notification Time:* {sub_data.get('preference_time', '09:00')}
━━━━━━━━━━━━━━━━━━━━━

*Quick Actions:*
/unsubscribe - Stop receiving updates
/settime HH:MM - Change notification time
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
        current_time = user_subscriptions.get(user_id, {}).get('preference_time', '09:00')
        await update.message.reply_text(
            f"⏰ Current notification time: *{current_time}*\n\n"
            f"To change it, use:\n"
            f"`/settime HH:MM`\n\n"
            f"Example: `/settime 14:30`\n"
            f"Example: `/settime 08:00`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        time_str = context.args[0]
        # Validate time format
        datetime.strptime(time_str, "%H:%M")
        
        if user_id not in user_subscriptions:
            # Auto-subscribe if not subscribed
            username = update.effective_user.username or "Unknown"
            first_name = update.effective_user.first_name or "User"
            user_subscriptions[user_id] = {
                'username': username,
                'first_name': first_name,
                'subscribed_at': datetime.now().isoformat(),
                'preference_time': time_str,
                'active': True
            }
            await update.message.reply_text(
                f"✅ You've been automatically subscribed!\n"
                f"⏰ Notification time set to {time_str}\n"
                f"📋 Use /mysubs to view your subscription."
            )
        else:
            user_subscriptions[user_id]['preference_time'] = time_str
            await update.message.reply_text(
                f"✅ Notification time updated to *{time_str}*!\n"
                f"🕐 You'll receive updates at this time daily.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        logger.info(f"User {user_id} set time to {time_str}")
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid time format!\n"
            "Please use HH:MM format (24-hour).\n\n"
            "Examples:\n"
            "✅ `/settime 09:00` - 9:00 AM\n"
            "✅ `/settime 14:30` - 2:30 PM\n"
            "✅ `/settime 23:59` - 11:59 PM",
            parse_mode=ParseMode.MARKDOWN
        )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bot status."""
    total_users = len(user_subscriptions)
    active_users = len([u for u in user_subscriptions.values() if u.get('active', True)])
    
    status_text = f"""
🤖 *Bot Status Report*

━━━━━━━━━━━━━━━━━━━━━
📌 *Bot Name:* {BOT_NAME}
🟢 *Status:* Online
📊 *Total Subscribers:* {total_users}
✅ *Active Users:* {active_users}
⏱️ *Uptime:* Running continuously
━━━━━━━━━━━━━━━━━━━━━

*Features:*
✅ 24/7 Operation
✅ Scheduled Updates
✅ Custom Time Settings
✅ Real-time Responses
✅ Inline Keyboard

*Commands:*
/help - Show all commands
/status - This status report

━━━━━━━━━━━━━━━━━━━━━
_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
"""
    await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'subscribe':
        # Create a new update object for the subscribe function
        await subscribe(update, context)
        await query.edit_message_text("✅ You've been subscribed!")
    elif query.data == 'view_subs':
        await my_subscriptions(update, context)
    elif query.data == 'help':
        await help_command(update, context)

async def send_daily_updates(context: ContextTypes.DEFAULT_TYPE):
    """Send daily tide updates to all active subscribers."""
    current_time = datetime.now().strftime("%H:%M")
    logger.info(f"Checking for scheduled updates at {current_time}...")
    
    # Generate tide information
    tide_info = generate_tide_info()
    
    sent_count = 0
    for user_id, data in user_subscriptions.items():
        if data.get('active', True):
            try:
                user_time = data.get('preference_time', '09:00')
                if current_time == user_time:
                    message = f"""
🌊 *Daily Tide Update* 🌊

━━━━━━━━━━━━━━━━━━━━━
📅 Date: {datetime.now().strftime('%B %d, %Y')}
⏰ Time: {current_time}
━━━━━━━━━━━━━━━━━━━━━

{tide_info}

━━━━━━━━━━━━━━━━━━━━━
ℹ️ _Stay informed about the tides!_

*Quick Actions:*
/unsubscribe - Stop updates
/settime - Change notification time
"""
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    sent_count += 1
                    logger.info(f"✅ Sent update to user {user_id}")
            except Exception as e:
                logger.error(f"❌ Failed to send message to {user_id}: {e}")
    
    if sent_count > 0:
        logger.info(f"📤 Sent {sent_count} updates at {current_time}")

def generate_tide_info():
    """Generate tide information."""
    import random
    tides = [
        f"""🌊 *Tide Report*

🔵 *High Tide:* 1.2m
⚪ *Low Tide:* 0.3m
🌊 *Wave Height:* 0.5m
💨 *Wind Speed:* 15 km/h
🌡️ *Temperature:* 22°C
📊 *Condition:* Moderate

*Best Time for:*
🏄 Surfing: Good
🎣 Fishing: Fair
🚣 Boating: Moderate""",

        f"""🌊 *Tide Report*

🔵 *High Tide:* 1.5m
⚪ *Low Tide:* 0.2m
🌊 *Wave Height:* 0.8m
💨 *Wind Speed:* 20 km/h
🌡️ *Temperature:* 24°C
📊 *Condition:* Strong

*Best Time for:*
🏄 Surfing: Excellent
🎣 Fishing: Good
🚣 Boating: Fair""",

        f"""🌊 *Tide Report*

🔵 *High Tide:* 0.8m
⚪ *Low Tide:* 0.1m
🌊 *Wave Height:* 0.3m
💨 *Wind Speed:* 10 km/h
🌡️ *Temperature:* 20°C
📊 *Condition:* Calm

*Best Time for:*
🏄 Surfing: Fair
🎣 Fishing: Excellent
🚣 Boating: Excellent""",

        f"""🌊 *Tide Report*

🔵 *High Tide:* 2.0m
⚪ *Low Tide:* 0.4m
🌊 *Wave Height:* 1.2m
💨 *Wind Speed:* 25 km/h
🌡️ *Temperature:* 21°C
📊 *Condition:* Rough

*Best Time for:*
🏄 Surfing: Excellent
🎣 Fishing: Poor
🚣 Boating: Caution""",

        f"""🌊 *Tide Report*

🔵 *High Tide:* 1.8m
⚪ *Low Tide:* 0.3m
🌊 *Wave Height:* 0.9m
💨 *Wind Speed:* 18 km/h
🌡️ *Temperature:* 23°C
📊 *Condition:* Good

*Best Time for:*
🏄 Surfing: Good
🎣 Fishing: Good
🚣 Boating: Good"""
    ]
    return random.choice(tides)

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands."""
    await update.message.reply_text(
        "❓ Unknown command.\n\n"
        "Use /help to see all available commands.\n"
        "Use /start to see the welcome message."
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"❌ Update {update} caused error: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ An error occurred. Please try again later.\n"
                "If this persists, contact the bot administrator."
            )
    except:
        pass

def main():
    """Start the bot."""
    logger.info("🚀 Starting bot application...")
    
    try:
        # Create application
        application = Application.builder().token(TOKEN).build()
        logger.info("✅ Application created")

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("subscribe", subscribe))
        application.add_handler(CommandHandler("unsubscribe", unsubscribe))
        application.add_handler(CommandHandler("mysubs", my_subscriptions))
        application.add_handler(CommandHandler("settime", set_time))
        application.add_handler(CommandHandler("status", status))
        logger.info("✅ Command handlers added")
        
        # Add callback handler for inline buttons
        application.add_handler(CallbackQueryHandler(handle_callback))
        logger.info("✅ Callback handler added")
        
        # Add fallback handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))
        
        # Add error handler
        application.add_error_handler(error_handler)
        logger.info("✅ Error handler added")
        
        # Schedule daily updates
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(send_daily_updates, interval=60.0, first=10)
            logger.info("✅ Scheduled job created (runs every minute)")
        else:
            logger.warning("⚠️ Job queue not available")
        
        logger.info("=" * 60)
        logger.info(f"✅ {BOT_NAME} is ready and running!")
        logger.info("=" * 60)
        logger.info("📌 Bot is polling for updates...")
        
        # Start the bot using polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
