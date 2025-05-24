from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ConversationHandler
from telegram.ext import MessageHandler, filters
from datetime import datetime
import sqlite3
import os
from dotenv import load_dotenv

import psycopg2
# States for conversation handler
SELECTING_MOOD, ADDING_NOTE = range(2)

# Check if the .env file exists
if os.path.exists('.env'):
    load_dotenv('.env')
else:
    print("No .env file found. Please create one with your bot token.")

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file. Please set it.")
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file. Please set it.")
# Database setup
def setup_database():
    #use postgresql
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS moods (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            mood TEXT NOT NULL,
            note TEXT,
            date TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_mood(user_id, mood, note=None):
    #change to postgresql
    conn= psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    formatted_date = datetime.now().strftime('%A, %B %d, %Y')
    cursor.execute('''
        INSERT INTO moods (user_id, mood, note,date)
        VALUES (%s, %s, %s, %s)
    ''', (user_id, mood, note, formatted_date))
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message with bot capabilities"""
    welcome_msg = """
🌟 *Welcome to Mood Diary Bot* 🌟

*I help you track your emotional journey!*

📌 *Main Features:*
- Daily mood logging (once per day)
- Mood statistics and trends
- Weekly reports with visual charts
- Secure private diary

📅 *Daily Usage:*
1. Use /mood to record how you feel
2. Add optional notes about your day
3. View insights with /stats or /weekly

🔍 *Try these commands:*
/mood - Record today's mood
/stats - View your mood statistics
/weekly - Weekly report with charts
/help - Show all commands

_Your data is private and stored securely._
"""
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def mood_for_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        print(f"User {update.effective_user.id} started mood tracking")
        
        if has_recorded_mood_today(update.effective_user.id):
            await update.message.reply_text("Already recorded today. Use /update")
            return ConversationHandler.END
            
        keyboard = [
            [InlineKeyboardButton("😊 Happy", callback_data='happy')],
            [InlineKeyboardButton("😢 Sad", callback_data='sad')],
            [InlineKeyboardButton("😠 Angry", callback_data='angry')],
            [InlineKeyboardButton("😐 Neutral", callback_data='neutral')]
        ]
        
        await update.message.reply_text(
            "Select your mood:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECTING_MOOD
        
    except Exception as e:
        print(f"Mood command error: {e}")
        await update.message.reply_text("Sorry, something went wrong. Try again later.")
        return ConversationHandler.END

async def mood_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    
    mood = query.data
    context.user_data['mood'] = mood
    
    # Different message if updating
    if context.user_data.get('is_update'):
        await query.edit_message_text(
            text=f"Updating to {mood.capitalize()}\n"
                 "Please update your note (or /skip to keep current note):"
        )
    else:
        await query.edit_message_text(
            text=f"Selected mood: {mood.capitalize()}\n"
                 "Would you like to add a note? (Type /skip to skip)"
        )
    
    return ADDING_NOTE

async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    note = update.message.text
    user_id = update.effective_user.id
    mood = context.user_data['mood']
    
    if context.user_data.get('is_update'):
        # Update existing entry
        #change to postgresql
        conn=psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE moods 
            SET mood = %s, note = %s, timestamp = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (mood, note, context.user_data['existing_id']))
        conn.commit()
        conn.close()
        await update.message.reply_text(
            f"Your entry has been updated to {mood} with note: {note}"
        )
    else:
        # Create new entry
        save_mood(user_id, mood, note)
        await update.message.reply_text(
            f"Your {mood} mood has been saved with note: {note}"
        )
    
    return ConversationHandler.END

async def skip_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    mood = context.user_data['mood']
    
    if context.user_data.get('is_update'):
        # Update mood but keep existing note
        conn = sqlite3.connect("mood_diary.db")
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE moods 
            SET mood = ?, timestamp = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (mood, context.user_data['existing_id']))
        conn.commit()
        conn.close()
        await update.message.reply_text(
            f"Your mood has been updated to {mood} (note unchanged)"
        )
    else:
        # New entry without note
        save_mood(user_id, mood, None)
        await update.message.reply_text(
            f"Your {mood} mood has been saved without a note"
        )
    
    return ConversationHandler.END

async def weekly_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    #change to postgresql
    conn=psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    
    # Get last 7 days of data
    cursor.execute('''
        SELECT mood, COUNT(*) as count 
        FROM moods
        WHERE user_id = %s
        AND date >= date('now', '-7 days')
        GROUP BY mood
    ''', (user_id,))
    results = cursor.fetchall()
    
    # Get total count for percentage calculation
    total = sum(count for _, count in results)
    
    if not results:
        await update.message.reply_text("No mood data found for the last week.")
        conn.close()
        return
    
    # Build stats message
    stats_message = "📈 *Weekly Mood Statistics*\n"
    stats_message += "────────────────────\n"
    
    # Add percentages and bar charts
    for mood, count in sorted(results, key=lambda x: x[1], reverse=True):
        percentage = (count / total) * 100
        bar = '█' * int(percentage / 5)  # Each █ represents 5%
        stats_message += (
            f"*{mood.capitalize()}*: {count} ({percentage:.1f}%)\n"
            f"{bar}\n\n"
        )
    
    stats_message += f"Total entries: {total}\n"
    stats_message += "────────────────────"
    
    conn.close()
    await update.message.reply_text(stats_message, parse_mode='Markdown')

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    #change to postgresql
    conn=psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT date, mood, note 
        FROM moods
        WHERE user_id = %s
        ORDER BY date DESC
    ''', (user_id,))
    results = cursor.fetchall()
    
    if not results:
        await update.message.reply_text("No mood entries found.")
        conn.close()
        return
    
    summary_message = "📝 *Your Mood History*\n"
    summary_message += "────────────────────\n"
    
    for date, mood, note in results:
        summary_message += (
            f"📅 *{date}*\n"
            f"🎭 Mood: {mood.capitalize()}\n"
        )
        if note:
            summary_message += f"📝 Note: {note}\n"
        summary_message += "────────────────────\n"
    
    summary_message += f"Total entries: {len(results)}"
    
    conn.close()
    
    # Split long messages to avoid hitting Telegram's limit
    if len(summary_message) > 4000:
        parts = [summary_message[i:i+4000] for i in range(0, len(summary_message), 4000)]
        for part in parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(summary_message, parse_mode='Markdown')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    #change to postgresql
    conn=psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute('''
        SELECT mood, COUNT(*) as count FROM moods
        WHERE user_id= %s
        GROUP BY mood
    ''', (user_id,))
    results = cursor.fetchall()
    conn.close()

    if not results:
        await update.message.reply_text("No mood data found.")
        return

    stats_message = "📊 Your mood statistics:\n"
    for mood, count in results:
        stats_message += f"- {mood.capitalize()}: {count}\n"

    await update.message.reply_text(stats_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all available commands with descriptions"""
    help_msg = """
📚 *Command Reference*

*Mood Tracking:*
/mood - Record your current mood (once per day)
/update - Change today's mood entry
/note - Add extra notes to today's mood

*Statistics:*
/stats - Your overall mood distribution
/weekly - Last 7 days report with charts
/summary - Full mood history timeline

*Data Management:*
/clear - Delete all your data (with confirmation)
/export - Get your data backup (coming soon)

*Support:*
/help - Show this message

🔹 *Usage Tips:*
- Moods are saved with timestamps
- Use /update if you change your mind
- Weekly reports generate every Sunday
"""
    await update.message.reply_text(help_msg, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation from either command or button"""
    # Clear context data
    context.user_data.clear()
    
    # Determine if this came from a message or callback
    if update.message:  # Regular command
        await update.message.reply_text(
            "Operation cancelled. You can start again with /mood."
        )
    elif update.callback_query:  # Inline button
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text="Operation cancelled. You can start again with /mood."
        )
    else:
        # Fallback for unexpected cases
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Operation cancelled."
            )
    
    return ConversationHandler.END

def has_recorded_mood_today(user_id: int) -> bool:
    """Check if user already recorded mood today"""
    conn = sqlite3.connect("mood_diary.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM moods 
        WHERE user_id = ? 
        AND DATE(timestamp) = DATE('now')
    ''', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def get_today_mood_entry(user_id: int) -> tuple:
    """Get today's mood entry if exists"""
    conn = sqlite3.connect("mood_diary.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, mood, note FROM moods 
        WHERE user_id = ? 
        AND DATE(timestamp) = DATE('now')
        LIMIT 1
    ''', (user_id,))
    entry = cursor.fetchone()
    conn.close()
    return entry

async def update_mood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for updating today's mood - shows current entry first"""
    user_id = update.effective_user.id
    
    # Check if user has an entry today
    entry = get_today_mood_entry(user_id)
    if not entry:
        await update.message.reply_text(
            "You haven't recorded a mood today yet.\n"
            "Use /mood to record your first mood of the day."
        )
        return ConversationHandler.END
    
    # Store existing data in context
    mood_id, current_mood, current_note = entry
    context.user_data['is_update'] = True
    context.user_data['existing_id'] = mood_id
    
    # Show current entry first
    await update.message.reply_text(
        f"📝 Previously saved mood: \n"
        f"🎭 Mood: {current_mood.capitalize()}\n"
        f"📝 Note: {current_note or 'No note'}\n\n"
        "Select your updated mood:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("😊 Happy", callback_data='happy')],
            [InlineKeyboardButton("😢 Sad", callback_data='sad')],
            [InlineKeyboardButton("😠 Angry", callback_data='angry')],
            [InlineKeyboardButton("😐 Neutral", callback_data='neutral')],
            [InlineKeyboardButton("❌ Cancel Update", callback_data='cancel_update')]
        ])
    )
    return SELECTING_MOOD

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear all mood history for the user"""
    user_id = update.effective_user.id
    
    # Create confirmation keyboard
    keyboard = [
        [InlineKeyboardButton("Yes, delete all", callback_data='confirm_clear')],
        [InlineKeyboardButton("Cancel", callback_data='cancel_clear')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ This will delete ALL your mood history permanently!\n"
        "Are you sure you want to continue?",
        reply_markup=reply_markup
    )

async def handle_clear_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the clear history confirmation"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'confirm_clear':
        conn = sqlite3.connect("mood_diary.db")
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM moods WHERE user_id = ?
        ''', (update.effective_user.id,))
        conn.commit()
        conn.close()
        
        await query.edit_message_text("All your mood history has been cleared.")
    else:
        await query.edit_message_text("Operation cancelled. Your data is safe.")

# Add these handlers to your setup:
def setup_handlers(application):
    # Update mood conversation with per_message=True
    update_handler = ConversationHandler(
        entry_points=[CommandHandler('update', update_mood)],
        states={
            SELECTING_MOOD: [
                CallbackQueryHandler(mood_selected, pattern='^(happy|sad|angry|neutral)$'),
                CallbackQueryHandler(cancel, pattern='cancel_update')
            ],
            ADDING_NOTE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_note),
                CommandHandler('skip', skip_note)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )
    
    # Main mood conversation with per_message=True
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('mood', mood_for_today)],
        states={
            SELECTING_MOOD: [
                CallbackQueryHandler(mood_selected, pattern='^(happy|sad|angry|neutral)$'),

            ],
            ADDING_NOTE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_note),
                CommandHandler('skip', skip_note)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )
    
    # Clear history handler
    clear_handler = CallbackQueryHandler(handle_clear_confirmation, pattern='^(confirm_clear|cancel_clear)$')
    
    application.add_handler(update_handler)
    application.add_handler(clear_handler)
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("weekly", weekly_stats))
    application.add_handler(CommandHandler("summary", summary))
    application.add_handler(CommandHandler("cancel", cancel))


def main() -> None:
    # Setup database
    setup_database()

    # Create application
    application = Application.builder() \
    .token(TELEGRAM_BOT_TOKEN) \
    .read_timeout(300) \
    .write_timeout(300) \
    .connect_timeout(300) \
    .pool_timeout(300) \
    .build() 
    
    # Setup all handlers
    setup_handlers(application)

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()