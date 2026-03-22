async def allow_in_dm(update):

    allowed = ["start", "ping", "info", "tr", "checkfw", "getrom"]

    chat = update.effective_chat

    if chat.type == "private":

        if not update.message.text:
            return False

        command = update.message.text.split()[0].replace("/", "")

        if command not in allowed:
            await update.message.reply_text(
                "This command only works in groups."
            )
            return False

    return True