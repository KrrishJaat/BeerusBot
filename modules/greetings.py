import json
import os
import random

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from modules.moderation import is_admin


GREET_FILE = "data/greetings.json"

if os.path.exists(GREET_FILE):
    with open(GREET_FILE, "r") as f:
        GREET_DB = json.load(f)
else:
    GREET_DB = {}


def save_greetings():
    with open(GREET_FILE, "w") as f:
        json.dump(GREET_DB, f, indent=4)


DEFAULT_WELCOME = [
    "Hey {fullname}, welcome to {chatname}!",
    "Welcome {fullname}! Glad you joined {chatname}.",
    "Hello {fullname}! Enjoy your stay in {chatname}.",
]

DEFAULT_BYE = [
    "Goodbye {fullname}, see you again!",
    "{fullname} left the chat.",
    "Sad to see you leave, {fullname}.",
]


# SET WELCOME
async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can set welcome message.")
        return

    text = " ".join(context.args)

    if not text:
        await update.message.reply_text("Usage:\n/setwelcome <message>")
        return

    chat_id = str(update.effective_chat.id)

    GREET_DB.setdefault(chat_id, {})
    GREET_DB[chat_id]["welcome"] = text

    save_greetings()

    await update.message.reply_text("Custom welcome message set.")


# SET BYE
async def setbye(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can set goodbye message.")
        return

    text = " ".join(context.args)

    if not text:
        await update.message.reply_text("Usage:\n/setbye <message>")
        return

    chat_id = str(update.effective_chat.id)

    GREET_DB.setdefault(chat_id, {})
    GREET_DB[chat_id]["bye"] = text

    save_greetings()

    await update.message.reply_text("Custom goodbye message set.")


# RESET COMMANDS
async def resetwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    chat_id = str(update.effective_chat.id)

    if chat_id in GREET_DB and "welcome" in GREET_DB[chat_id]:
        del GREET_DB[chat_id]["welcome"]

    save_greetings()

    await update.message.reply_text("Welcome message reset to default.")


async def resetbye(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    chat_id = str(update.effective_chat.id)

    if chat_id in GREET_DB and "bye" in GREET_DB[chat_id]:
        del GREET_DB[chat_id]["bye"]

    save_greetings()

    await update.message.reply_text("Goodbye message reset to default.")


# NEW MEMBER
async def welcome_member(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat
    chat_id = str(chat.id)

    for user in update.message.new_chat_members:

        if chat_id in GREET_DB and "welcome" in GREET_DB[chat_id]:
            template = GREET_DB[chat_id]["welcome"]
        else:
            template = random.choice(DEFAULT_WELCOME)

        text = template.format(
            fullname=user.full_name,
            username=f"@{user.username}" if user.username else "None",
            id=user.id,
            chatname=chat.title
        )

        await update.message.reply_text(text)


# LEFT MEMBER
async def goodbye_member(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat
    chat_id = str(chat.id)

    user = update.message.left_chat_member

    if chat_id in GREET_DB and "bye" in GREET_DB[chat_id]:
        template = GREET_DB[chat_id]["bye"]
    else:
        template = random.choice(DEFAULT_BYE)

    text = template.format(
        fullname=user.full_name,
        username=f"@{user.username}" if user.username else "None",
        id=user.id,
        chatname=chat.title
    )

    await update.message.reply_text(text)


def register_greetings(app):

    app.add_handler(CommandHandler("setwelcome", setwelcome))
    app.add_handler(CommandHandler("setbye", setbye))
    app.add_handler(CommandHandler("resetwelcome", resetwelcome))
    app.add_handler(CommandHandler("resetbye", resetbye))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_member))