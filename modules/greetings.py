import json
import os
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import mention_html
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ChatMemberHandler,
)

from modules.moderation import is_admin

GREET_FILE = "data/greetings.json"

# LOAD DB
if os.path.exists(GREET_FILE):
    with open(GREET_FILE, "r") as f:
        GREET_DB = json.load(f)
else:
    GREET_DB = {}


def save_greetings():
    with open(GREET_FILE, "w") as f:
        json.dump(GREET_DB, f, indent=4)


# ---------------- COMMANDS ---------------- #

async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Admins only.")

    chat_id = str(update.effective_chat.id)
    GREET_DB.setdefault(chat_id, {})

    msg = update.message

    # ---------------- CASE 1: REPLY ----------------
    if msg.reply_to_message:
        target = msg.reply_to_message

        if target.photo:
            GREET_DB[chat_id]["welcome"] = "media"
            GREET_DB[chat_id]["media_type"] = "photo"
            GREET_DB[chat_id]["file_id"] = target.photo[-1].file_id

        elif target.animation:
            GREET_DB[chat_id]["welcome"] = "media"
            GREET_DB[chat_id]["media_type"] = "gif"
            GREET_DB[chat_id]["file_id"] = target.animation.file_id

        else:
            return await msg.reply_text("Reply to photo or gif.")

        # ✅ MULTILINE SUPPORT
        if len(msg.text.split(None, 1)) > 1:
            GREET_DB[chat_id]["text"] = msg.text.split(None, 1)[1]
        else:
            GREET_DB[chat_id]["text"] = ""

    # ---------------- CASE 2: DIRECT PHOTO/GIF ----------------
    elif msg.photo or msg.animation:

        GREET_DB[chat_id]["welcome"] = "media"

        if msg.photo:
            GREET_DB[chat_id]["media_type"] = "photo"
            GREET_DB[chat_id]["file_id"] = msg.photo[-1].file_id

        elif msg.animation:
            GREET_DB[chat_id]["media_type"] = "gif"
            GREET_DB[chat_id]["file_id"] = msg.animation.file_id

        caption = msg.caption or ""

        # remove "/setwelcome" from caption
        if caption.startswith("/setwelcome"):
            parts = caption.split(None, 1)
            caption = parts[1] if len(parts) > 1 else ""

        GREET_DB[chat_id]["text"] = caption.strip()

    # ---------------- CASE 3: TEXT ONLY ----------------
    else:
        if len(msg.text.split(None, 1)) < 2:
            return await msg.reply_text("Usage:\n/setwelcome <text>")

        text = msg.text.split(None, 1)[1]

        GREET_DB[chat_id]["welcome"] = text

    save_greetings()
    await msg.reply_text("✅ Welcome message saved!")


async def setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return

    chat_id = str(update.effective_chat.id)
    text = " ".join(context.args)

    if not text:
        return await update.message.reply_text("Usage: /setrules <rules text>")

    GREET_DB.setdefault(chat_id, {})
    GREET_DB[chat_id]["rules"] = text
    save_greetings()

    await update.message.reply_text("✅ Rules set!")


# ---------------- MAIN ---------------- #
async def member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    chat = update.effective_chat
    chat_id = str(chat.id)

    old = result.old_chat_member
    new = result.new_chat_member
    user = new.user

    user_mention = mention_html(user.id, user.full_name)

    if chat.username:
        chat_link = f"<a href='https://t.me/{chat.username}'>{chat.title}</a>"
    else:
        chat_link = chat.title

    # JOIN
    if new.status in ["member", "administrator"] and old.status in ["left", "kicked"]:

        data = GREET_DB.get(chat_id, {})

        # RULE BUTTON
        keyboard = None
        if "rules" in data:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📜 Rules", callback_data="show_rules")]
            ])

        # MEDIA WELCOME
        if data.get("welcome") == "media":

            caption = data.get("text", "").format(
                user=user_mention,
                chat=chat_link
            )

            if data["media_type"] == "photo":
                msg = await chat.send_photo(
                    data["file_id"],
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )

            elif data["media_type"] == "gif":
                msg = await chat.send_animation(
                    data["file_id"],
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )

        else:
            template = data.get(
                "welcome",
                "✨ <b>Welcome</b> {user}!\n\n📌 {chat}"
            )

            text = template.format(user=user_mention, chat=chat_link)

            msg = await chat.send_message(
                text,
                parse_mode="HTML",
                reply_markup=keyboard
            )

        context.application.create_task(auto_delete(msg))

    # LEAVE
    elif old.status in ["member", "administrator", "creator"] and new.status in ["left", "kicked"]:

        data = GREET_DB.get(chat_id, {})

        template = data.get(
            "bye",
            "👋 {user} left the chat."
        )

        text = template.format(user=user_mention, chat=chat_link)

        msg = await chat.send_message(text, parse_mode="HTML")

        context.application.create_task(auto_delete(msg))


# RULE BUTTON CLICK
async def rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = str(update.effective_chat.id)

    rules = GREET_DB.get(chat_id, {}).get("rules", "No rules set.")

    await query.answer()
    await query.message.reply_text(rules)


# CLEAN SERVICE
async def clean_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if msg and (msg.new_chat_members or msg.left_chat_member):
        try:
            await msg.delete()
        except:
            pass

# SET BYE
async def setbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Admins only.")

    chat_id = str(update.effective_chat.id)
    GREET_DB.setdefault(chat_id, {})

    msg = update.message

    # ✅ MULTILINE SUPPORT
    if len(msg.text.split(None, 1)) < 2:
        return await msg.reply_text("Usage:\n/setbye <message>")

    text = msg.text.split(None, 1)[1]

    GREET_DB[chat_id]["bye"] = text
    save_greetings()

    await msg.reply_text("✅ Goodbye message set!")

# REGISTER
def register_greetings(app):

    app.add_handler(CommandHandler("setwelcome", setwelcome))
    app.add_handler(CommandHandler("setbye", setbye))
    app.add_handler(CommandHandler("setrules", setrules))

    app.add_handler(ChatMemberHandler(member_update, ChatMemberHandler.CHAT_MEMBER))

    app.add_handler(MessageHandler(filters.ALL, clean_service), group=-1)

    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(rules_callback, pattern="show_rules"))