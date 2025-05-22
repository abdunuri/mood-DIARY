# Mood Diary Telegram Bot 🌟

A Telegram bot for tracking daily moods with statistics and analytics.

## Features

- ✅ Daily mood logging (Happy, Sad, Angry, Neutral)
- 📊 Weekly statistics with visual charts
- 📝 Note-taking with each mood entry
- 🔄 Update existing entries
- 📅 History and summary views
- 🗑️ Data clearing functionality

## Commands
/start - Welcome message
/mood - Record today's mood
/update - Update today's mood
/stats - View mood statistics
/weekly - Weekly mood report
/summary - Full mood history
/clear - Delete all your data
/help - Show all commands


## Setup

### Prerequisites

- Python 3.8+
- Docker (optional)
- Telegram Bot Token

### Local Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/abdunuri/mood-DIARY
   cd mood-DIARY
Create and activate virtual environment:

bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate    # Windows
Install dependencies:

bash
pip install -r requirements.txt
Create .env file:

bash
echo "TELEGRAM_BOT_TOKEN=your_bot_token_here" > .env
Run the bot:

bash
python main.py
Docker Setup
Build the image:

bash
docker build -t mood-diary-bot .
Run the container:

bash
docker run -d --name mood-bot -e TELEGRAM_BOT_TOKEN=your_token_here mood-diary-bot
Database
The bot uses SQLite stored in mood_diary.db. For Docker, mount a volume to persist data:

bash
docker run -d -v ./mood_data:/app mood-diary-bot
Requirements
python-telegram-bot==20.3

python-dotenv==1.0.0

sqlite3 (built-in)

License
MIT License

