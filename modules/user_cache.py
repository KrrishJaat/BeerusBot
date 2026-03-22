import json
import os

from telegram import Update
from telegram.ext import MessageHandler, ContextTypes, filters


USER_FILE = "data/users.json"

# load database
if os.path.exists(USER_FILE):
    with open(USER_FILE, "r") as f:
        USERS = json.load(f)
else:
    USERS = {}


def save():
    with open(USER_FILE, "w") as f:
        json.dump(USERS, f)


# cache users whenever they send a message
async def cache_user(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user = update.effective_user

    if not user.username:
        return

    USERS[user.username.lower()] = user.id
    save()


def register_user_cache(app):

    app.add_handler(
        MessageHandler(filters.ALL, cache_user),
        group=10
    )