import json

from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters

from modules.moderation import is_admin
from utils import load_json, save_json


notes_file = "data/notes.json"
notes_db = load_json(notes_file)


# SAVE NOTE
async def save_note(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can save notes.")
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage:\n/save <name> <text>\nOR reply to a message with /save <name>"
        )
        return

    name = context.args[0].lower()
    chat_id = str(update.effective_chat.id)

    if chat_id not in notes_db:
        notes_db[chat_id] = {}

    # Reply save
    if update.message.reply_to_message:

        reply_msg = update.message.reply_to_message

        if reply_msg.text:
            notes_db[chat_id][name] = reply_msg.text

        elif reply_msg.caption:
            notes_db[chat_id][name] = reply_msg.caption

        else:
            await update.message.reply_text(
                "Only text messages can be saved right now."
            )
            return

    else:

        if len(context.args) < 2:
            await update.message.reply_text(
                "Provide text or reply to a message."
            )
            return

        text = " ".join(context.args[1:])
        notes_db[chat_id][name] = text

    save_json(notes_file, notes_db)

    await update.message.reply_text(
        f"Note `{name}` saved.",
        parse_mode="Markdown"
    )


# GET NOTE
async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /get <note>")
        return

    name = context.args[0].lower()
    chat_id = str(update.effective_chat.id)

    if chat_id in notes_db and name in notes_db[chat_id]:

        await update.message.reply_text(
            notes_db[chat_id][name]
        )

    else:
        await update.message.reply_text("Note not found.")


# LIST NOTES
async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = str(update.effective_chat.id)
    chat_name = update.effective_chat.title

    if chat_id not in notes_db or not notes_db[chat_id]:

        await update.message.reply_text(
            f"No Notes Saved In {chat_name}"
        )
        return

    text = f"📒 Notes Saved In {chat_name}\n\n"

    for note in notes_db[chat_id]:

        text += f"• {note}\n"

    await update.message.reply_text(text)


# DELETE NOTE
async def clear_note(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        await update.message.reply_text(
            "Only admins can delete notes."
        )
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /clear <note>"
        )
        return

    name = context.args[0].lower()
    chat_id = str(update.effective_chat.id)

    if chat_id in notes_db and name in notes_db[chat_id]:

        del notes_db[chat_id][name]

        save_json(notes_file, notes_db)

        await update.message.reply_text("Note removed.")

    else:
        await update.message.reply_text("Note not found.")


# QUICK NOTE TRIGGER (#note)
async def hashtag_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if not text.startswith("#"):
        return

    name = text[1:].lower()
    chat_id = str(update.effective_chat.id)

    if chat_id in notes_db and name in notes_db[chat_id]:

        await update.message.reply_text(
            notes_db[chat_id][name]
        )


# REGISTER HANDLERS
def register_notes(app):

    app.add_handler(CommandHandler("save", save_note), group=0)
    app.add_handler(CommandHandler("get", get_note), group=0)
    app.add_handler(CommandHandler("notes", list_notes), group=0)
    app.add_handler(CommandHandler("clear", clear_note), group=0)

    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex("^#"), hashtag_notes),
        group=2
    )
