@echo off
REM Odin v2 - Daily Sync + Bot Restart
REM Scheduled via Windows Task Scheduler to run at 5:00 AM daily

echo [%date% %time%] Starting daily sync...

cd /d C:\Users\ASUS\.gemini\antigravity\scratch\odin-v2

REM 1. Run daily sync (incremental update of all 12 tables)
python ingestion/daily_sync.py >> logs\daily_sync_%date:~-4,4%%date:~-7,2%%date:~-10,2%.log 2>&1

echo [%date% %time%] Daily sync complete.

REM 2. [DISABLED LOCAL BOT STARTUP]
REM The bot runs in production on GCP Cloud Run. Running it locally in polling
REM mode deletes the production webhook and hijacks updates, causing BQ access errors.
REM Local bot startup is disabled here.
