from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from config import OWNER_ID


# REPORT BUG COMMAND
async def report_bug(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /reportbug <bug>")
        return

    bug_text = " ".join(context.args)

    user = update.effective_user
    chat = update.effective_chat

    username = f"@{user.username}" if user.username else "No username"

    message = (
        "🐞 Bug Report\n\n"
        f"{bug_text}\n\n"
        f"Reported by: {username}\n"
        f"User ID: {user.id}\n"
        f"Chat: {chat.title if chat.title else 'Private'}"
    )

    try:
        await context.bot.send_message(OWNER_ID, message)

        await update.message.reply_text(
            "✅ Bug reported successfully."
        )

    except:
        await update.message.reply_text(
            "❌ Failed to send bug report."
        )


# REGISTER COMMAND
def register_report(app):

    app.add_handler(CommandHandler("reportbug", report_bug), group=0)