import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes

from config import REPO_OWNER, REPO_NAME


async def getrom(update: Update, context: ContextTypes.DEFAULT_TYPE):

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

    try:

        r = requests.get(url, timeout=10)
        data = r.json()

        tag = data.get("tag_name", "Unknown")
        name = data.get("name", "Latest Release")
        body = data.get("body", "")
        html_url = data.get("html_url")

        assets = data.get("assets", [])

        download_url = None

        if assets:
            download_url = assets[0].get("browser_download_url")

        text = (
            "🚀 Latest ReCoreUI Release\n\n"
            f"Version: {tag}\n"
            f"Title: {name}\n\n"
        )

        keyboard = []

        if download_url:
            keyboard.append(
                [InlineKeyboardButton("⬇ Download ROM", url=download_url)]
            )

        keyboard.append(
            [InlineKeyboardButton("📄 View Release Page", url=html_url)]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            text,
            reply_markup=reply_markup
        )

    except Exception as e:
        print(e)
        await update.message.reply_text(
            "Failed to fetch latest ROM release."
        )


def register_getrom(app):
    app.add_handler(CommandHandler("getrom", getrom), group=0)