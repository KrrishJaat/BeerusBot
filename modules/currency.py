import requests

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


# CURRENCY CONVERTER
async def convert_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):

    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "Usage:\n/convert <amount> <from> <to>\nExample: /convert 1 usd inr"
        )
        return

    # Case: /convert usd inr
    if len(args) == 2:
        amount = 1
        from_cur = args[0].upper()
        to_cur = args[1].upper()

    # Case: /convert 10 usd inr
    else:
        try:
            amount = float(args[0])
        except:
            await update.message.reply_text("Invalid amount.")
            return

        from_cur = args[1].upper()
        to_cur = args[2].upper()

    url = f"https://api.exchangerate-api.com/v4/latest/{from_cur}"

    try:
        data = requests.get(url).json()

        rate = data["rates"][to_cur]

        result = amount * rate

        await update.message.reply_text(
            f"💱 Currency Converter\n\n"
            f"{amount} {from_cur} = {result:.2f} {to_cur}"
        )

    except:
        await update.message.reply_text("Invalid currency code.")


# REGISTER COMMAND
def register_currency(app):

    app.add_handler(CommandHandler("convert", convert_currency), group=0)
