# LUCIFER-Try: standalone file-search starter

This is a **small replacement starter bot**, not the original LUCIFER feature-complete code. The source repository's main branch did not include `bot.py` although its startup process expected that file. This branch runs the bot's code from this repository rather than cloning another repository at startup.

## Required environment variables (set privately in your hosting provider)
- `BOT_TOKEN`: Telegram bot token from @BotFather.
- `API_ID` and `API_HASH`: Telegram app credentials from https://my.telegram.org.
- `DATABASE_URI`: MongoDB Atlas connection string.

## Optional variables
- `DATABASE_NAME`: Defaults to `lucifer`.
- `CHANNELS`: Space-separated numeric Telegram channel IDs, e.g. `-1001234567890 -1009876543210`. Set this in production to prevent indexing unwanted channels.
- `ADMINS`: Space-separated numeric Telegram user IDs, authorized for /stats. Set this in production.

## Run on a server
Build/deploy this repo as a background worker using the Dockerfile or run:
```sh
pip install -r requirements.txt
python bot.py
```

The bot must be an administrator of every channel you want to index and must receive new channel posts. It **does not retroactively index old messages**. In a private chat, use /start and send the file/movie name to search, then click a result button to receive a copy. Searches are plain text matches in filenames or captions (up to 10 matches). This starter does not implement original LUCIFER's full feature set, inline mode, subscription checks, or advanced filtering.

Never commit bot tokens, API hashes, session strings, or MongoDB credentials into this public repository. Enter secrets only in the hosting provider's environment-variable settings.
