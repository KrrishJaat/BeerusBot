import json
import os
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from config import OWNER_ID

LOG_FILE = "data/log_channel.json"

# Load log channel
if os.path.exists(LOG_FILE):
    with open(LOG_FILE) as f:
        data = json.load(f)
        LOG_CHANNEL = data.get("log_channel")
else:
    LOG_CHANNEL = None


def save_log_channel(channel_id):
    with open(LOG_FILE, "w") as f:
        json.dump({"log_channel": channel_id}, f, indent=4)


# SET GLOBAL LOG CHANNEL (OWNER ONLY, DM ONLY)
async def setlog(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    if update.effective_chat.type != "private":
        await update.message.reply_text("Use this command in bot DM.")
        return

    if not context.args:
        await update.message.reply_text("Usage:\n/setlogchannel <channel_id>")
        return

    global LOG_CHANNEL

    channel_id = context.args[0]

    LOG_CHANNEL = channel_id
    save_log_channel(channel_id)

    await update.message.reply_text("Global log channel set successfully.")


# REMOVE LOG CHANNEL
async def removelog(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    if update.effective_chat.type != "private":
        return

    global LOG_CHANNEL

    LOG_CHANNEL = None

    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    await update.message.reply_text("Global log channel removed.")


# SEND LOG
async def send_log(context, chat_id, action, user=None, admin=None, reason=None, message=None):

    if not LOG_CHANNEL:
        return

    try:
        chat = await context.bot.get_chat(chat_id)

        group_name = chat.title
        group_link = f"https://t.me/c/{str(chat_id)[4:]}/1"

        text = f"📢 <b>Log from:</b> <a href='{group_link}'>{group_name}</a>\n\n"

        text += f"<b>Action:</b> {action}\n"

        if user:
            text += f"👤 <b>User:</b> <a href='tg://user?id={user.id}'>{user.first_name}</a>\n"

        if admin:
            text += f"🛡 <b>Admin:</b> <a href='tg://user?id={admin.id}'>{admin.first_name}</a>\n"

        if reason:
            text += f"📄 <b>Reason:</b> {reason}\n"

        if message:
            link = f"https://t.me/c/{str(chat_id)[4:]}/{message.message_id}"
            text += f"\n🔗 <a href='{link}'>Jump to message</a>"

        await context.bot.send_message(
            LOG_CHANNEL,
            text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    except Exception as e:
        print("LOG ERROR:", e)


def register_adminlogs(app):

    app.add_handler(CommandHandler("setlogchannel", setlog))
    app.add_handler(CommandHandler("removelogchannel", removelog))