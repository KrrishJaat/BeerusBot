import requests
import urllib.parse

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


LANGUAGES = {
    "af": "Afrikaans",
    "ar": "Arabic",
    "bn": "Bengali",
    "bg": "Bulgarian",
    "zh-cn": "Chinese",
    "hr": "Croatian",
    "cs": "Czech",
    "da": "Danish",
    "nl": "Dutch",
    "en": "English",
    "fi": "Finnish",
    "fr": "French",
    "de": "German",
    "el": "Greek",
    "hi": "Hindi",
    "hu": "Hungarian",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "ml": "Malayalam",
    "mr": "Marathi",
    "ne": "Nepali",
    "no": "Norwegian",
    "pl": "Polish",
    "pt": "Portuguese",
    "pa": "Punjabi",
    "ro": "Romanian",
    "ru": "Russian",
    "es": "Spanish",
    "sv": "Swedish",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese"
}


async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message

    if not message.reply_to_message:
        await message.reply_text(
            "Reply to a message to translate it.\nExample:\n/tr en"
        )
        return

    if not context.args:
        await message.reply_text(
            "Usage: /tr <language_code>\nExample: /tr en"
        )
        return

    target_lang = context.args[0].lower()

    reply = message.reply_to_message
    text = reply.text or reply.caption

    if not text:
        await message.reply_text("No text found to translate.")
        return

    encoded = urllib.parse.quote_plus(text)

    url = (
        f"https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl=auto&tl={target_lang}&dt=t&q={encoded}"
    )

    try:

        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            await message.reply_text("Translation failed.")
            return

        data = r.json()

        translated = ""
        for item in data[0]:
            translated += item[0]

        source_lang = data[2]

        source_name = LANGUAGES.get(source_lang, source_lang.upper())
        target_name = LANGUAGES.get(target_lang, target_lang.upper())

        await message.reply_text(
            f"🌐 Translation\n\n"
            f"From: {source_name}\n"
            f"To: {target_name}\n\n"
            f"{translated}"
        )

    except Exception:
        await message.reply_text("Translation error.")


def register_translate(app):
    app.add_handler(CommandHandler(["tr", "tl"], translate), group=0)