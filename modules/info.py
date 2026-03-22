from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from modules.moderation import ADMIN_RANKS
from modules.user_cache import USERS


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.message

    # 1️⃣ reply method
    if message.reply_to_message:
        user = message.reply_to_message.from_user

    # 2️⃣ username argument
    elif context.args:

        username = context.args[0].replace("@", "").lower()

        if username in USERS:

            uid = USERS[username]

            try:
                user = await context.bot.get_chat(uid)
            except:
                await message.reply_text("User not accessible.")
                return

        else:
            await message.reply_text("User not found in my database.")
            return

    # 3️⃣ self info
    else:
        user = update.effective_user


    uid = user.id
    first = user.first_name or ""
    last = user.last_name or ""
    name = f"{first} {last}".strip()

    # clickable name
    name_link = f"[{name}](tg://user?id={uid})"

    username = user.username
    rank = ADMIN_RANKS.get(str(uid), "User").upper()

    text = (
        "👤 User Information\n\n"
        f"Name: {name_link}\n"
        f"ID: `{uid}`\n"
    )

    if username:
        text += f"Username: @{username}\n"

    text += f"\nRank: {rank}"

    await message.reply_text(text, parse_mode="Markdown")


def register_info(app):
    app.add_handler(CommandHandler("info", info), group=0)