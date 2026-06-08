# Mood Diary Telegram Bot

Mood Diary is a Telegram bot for recording daily moods, adding short notes, and reviewing personal mood history through simple bot commands.

## Main Concept

The bot gives each user a private mood journal inside Telegram. Users can log one mood per day, attach an optional note, update the current day's entry, and view statistics or history from the SQLite database.

## Features

- Daily mood logging with inline buttons
- Optional note for each mood entry
- Update today's saved mood
- Overall mood statistics
- Weekly mood summary
- Full mood history
- Clear all saved mood data with confirmation

## Tech Stack

- Python
- `python-telegram-bot`
- SQLite
- `python-dotenv`

## Setup

```bash
pip install -r requirements.txt
```

Create `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
```

Run:

```bash
python main.py
```

## Data Storage

Mood entries are stored locally in `mood_diary.db`. Keep that file backed up if the bot is used long term.
