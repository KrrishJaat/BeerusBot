import requests
from bs4 import BeautifulSoup

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes


headers = {
    "User-Agent": "Mozilla/5.0"
}


async def checkfw(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage:\n/checkfw <model> <csc>\nExample:\n/checkfw m146b ins"
        )
        return

    model = context.args[0].upper()
    csc = context.args[1].upper()

    if not model.startswith("SM-"):
        model = f"SM-{model}"

    url = f"https://fota-cloud-dn.ospserver.net/firmware/{csc}/{model}/version.xml"

    try:
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            await update.message.reply_text("Firmware not found.")
            return

        page = BeautifulSoup(r.content, "xml")

        latest = page.find("latest")

        if not latest:
            await update.message.reply_text("No public firmware release found.")
            return

        android = latest.get("o")

        pda, csc_v, phone = latest.text.strip().split("/")

        text = (
            f"📱 Samsung Firmware\n\n"
            f"Device: {model}\n"
            f"CSC: {csc}\n\n"
            f"PDA: `{pda}`\n"
            f"CSC: `{csc_v}`\n"
            f"Phone: `{phone}`\n"
        )

        if android:
            text += f"Android: `{android}`\n"

        samfw_page = f"https://samfw.com/firmware/{model}/{csc}"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬇ Download Firmware", url=samfw_page)]
        ])

        await update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    except Exception as e:
        print("Firmware error:", e)
        await update.message.reply_text(
            "Failed to fetch firmware information."
        )


def register_firmware(app):
    app.add_handler(CommandHandler("checkfw", checkfw), group=0)