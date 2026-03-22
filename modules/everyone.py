import json

from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters

from modules.moderation import is_admin


users_file = "data/users.json"

try:
    with open(users_file, "r") as f:
        users_db = json.load(f)
except:
    users_db = {}


def save():
    with open(users_file, "w") as f:
        json.dump(users_db, f)


# track users
async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    chat = str(update.effective_chat.id)
    user = update.effective_user.id

    if chat not in users_db:
        users_db[chat] = []

    if user not in users_db[chat]:
        users_db[chat].append(user)
        save()


# everyone command
async def everyone(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        await update.message.reply_text("Bitch You're Not Worthy.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /everyone <message>")
        return

    chat = str(update.effective_chat.id)

    if chat not in users_db:
        await update.message.reply_text("No users recorded yet.")
        return

    reason = " ".join(context.args)

    admin = update.effective_user.first_name

    text = (
        f"📢 Everyone Attention\n\n"
        f"From: {admin}\n"
        f"Message: {reason}\n\n"
    )

    mentions = ""

    for uid in users_db[chat]:
        mentions += f"[‎](tg://user?id={uid})"

    await update.message.reply_text(text + mentions, parse_mode="Markdown")


def register_everyone(app):

    app.add_handler(CommandHandler("everyone", everyone))

    # track users silently
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), track))
    group=3
