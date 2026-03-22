import json
import os
from telegram import Update
from telegram.ext import MessageHandler, filters

GROUP_FILE = "data/groups.json"

if os.path.exists(GROUP_FILE):
    with open(GROUP_FILE) as f:
        GROUPS = json.load(f)
else:
    GROUPS = []


def save_groups():
    with open(GROUP_FILE, "w") as f:
        json.dump(GROUPS, f)


async def track_groups(update: Update, context):

    chat = update.effective_chat

    if chat.type not in ["group", "supergroup"]:
        return

    if chat.id not in GROUPS:
        GROUPS.append(chat.id)
        save_groups()

async def bot_removed(update: Update, context):

    chat = update.effective_chat

    if chat.id in GROUPS:
        GROUPS.remove(chat.id)
        save_groups()

def register_groups(app):
    app.add_handler(MessageHandler(filters.ALL, track_groups), group=5)
    app.add_handler(
    MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, bot_removed),
    group=5
)
