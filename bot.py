"""Standalone Telegram file index/search bot.

Required environment: BOT_TOKEN, API_ID, API_HASH, DATABASE_URI.
Optional: DATABASE_NAME, CHANNELS, ADMINS.
"""
import logging
import os
import re

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("lucifer")

def required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

BOT_TOKEN = required("BOT_TOKEN")
API_ID = int(required("API_ID"))
API_HASH = required("API_HASH")
DATABASE_URI = required("DATABASE_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "lucifer")
CHANNELS = {int(v) for v in os.getenv("CHANNELS", "").split() if v.lstrip("-").isdigit()}
ADMINS = {int(v) for v in os.getenv("ADMINS", "").split() if v.isdigit()}

mongo = MongoClient(DATABASE_URI, serverSelectionTimeoutMS=12000)
files = mongo[DATABASE_NAME]["telegram_files"]
files.create_index([("chat_id", 1), ("message_id", 1)], unique=True)
app = Client("lucifer-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

def get_media(message):
    for kind in ("document", "video", "audio", "photo", "animation"):
        media = getattr(message, kind, None)
        if media:
            return kind, media
    return None, None

@app.on_message(filters.command(["start", "help"]) & filters.private)
async def start(client, message):
    await message.reply_text(
        "Hello! I index new files posted in my configured Telegram channels. "
        "Send a movie or filename here to search. Use /stats for the file count. "
        "I cannot search messages from before I joined a channel."
    )

@app.on_message(filters.command("stats") & filters.private)
async def stats(client, message):
    if ADMINS and message.from_user.id not in ADMINS:
        await message.reply_text("This command is for admins.")
        return
    await message.reply_text(f"Indexed files: {files.count_documents({}):,}")

@app.on_message(filters.channel)
async def index_channel(client, message):
    if CHANNELS and message.chat.id not in CHANNELS:
        return
    kind, media = get_media(message)
    if not media:
        return
    title = (getattr(media, "file_name", None) or message.caption or
             f"{kind} {message.id}")[:500]
    caption = (message.caption or "")[:1000]
    try:
        files.update_one(
            {"chat_id": message.chat.id, "message_id": message.id},
            {"$set": {"file_id": media.file_id, "kind": kind,
                      "title": title, "caption": caption}},
            upsert=True,
        )
        log.info("Indexed %s/%s", message.chat.id, message.id)
    except PyMongoError:
        log.exception("Could not index channel message")

@app.on_message(filters.private & filters.text, group=1)
async def search(client, message):
    query = message.text.strip()
    if query.startswith("/"):
        return
    if len(query) < 2:
        await message.reply_text("Enter at least 2 characters.")
        return
    pattern = re.escape(query[:100])
    try:
        matches = list(files.find(
            {"$or": [{"title": {"$regex": pattern, "$options": "i"}},
                     {"caption": {"$regex": pattern, "$options": "i"}}]}
        ).limit(10))
    except PyMongoError:
        log.exception("Search failed")
        await message.reply_text("Search is temporarily unavailable.")
        return
    if not matches:
        await message.reply_text("No matching files yet.")
        return
    buttons = [
        [InlineKeyboardButton(
            f"{doc['title'][:55]}", callback_data=f"file:{doc['_id']}"
        )] for doc in matches
    ]
    await message.reply_text("Choose a file:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^file:"))
async def deliver(client, query):
    try:
        record = files.find_one({"_id": ObjectId(query.data[5:])})
    except (InvalidId, PyMongoError):
        record = None
    if not record:
        await query.answer("File not found.", show_alert=True)
        return
    try:
        await client.send_cached_media(
            query.from_user.id, record["file_id"],
            caption=record.get("caption", "")[:1000] or None,
        )
        await query.answer("Sent to your private chat!")
    except Exception:
        log.exception("File delivery failed")
        await query.answer("Unable to send file. Start the bot in private first.", show_alert=True)

if __name__ == "__main__":
    log.info("Starting LUCIFER file search bot")
    app.run()
