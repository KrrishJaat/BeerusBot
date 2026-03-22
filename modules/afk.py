from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime

afk_users = {}


# AFK COMMAND
async def afk(update: Update, context: ContextTypes.DEFAULT_TYPE):

    reason = " ".join(context.args)

    user = update.effective_user

    afk_users[user.id] = {
        "reason": reason,
        "time": datetime.now()
    }

    if reason:
        await update.message.reply_text(
            f"{user.first_name} is now AFK\nReason: {reason}"
        )
    else:
        await update.message.reply_text(
            f"{user.first_name} is now AFK"
        )


# AFK MESSAGE CHECK
async def check_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    # ignore /afk command message
    if update.message.text and update.message.text.startswith("/afk"):
        return

    user = update.effective_user

    # USER RETURNS FROM AFK
    if user.id in afk_users:

        afk_data = afk_users[user.id]
        afk_time = afk_data["time"]

        duration = datetime.now() - afk_time
        seconds = int(duration.total_seconds())

        if seconds < 60:
            time_text = f"{seconds} seconds"
        else:
            time_text = f"{seconds // 60} minutes"

        del afk_users[user.id]

        await update.message.reply_text(
            f"Welcome back {user.first_name}\nAFK for {time_text}"
        )

    # REPLY DETECTION
    if update.message.reply_to_message:

        replied_user = update.message.reply_to_message.from_user

        if replied_user.id in afk_users:

            afk_data = afk_users[replied_user.id]
            reason = afk_data["reason"]
            afk_time = afk_data["time"]

            duration = datetime.now() - afk_time
            minutes = int(duration.total_seconds() / 60)

            if reason:
                await update.message.reply_text(
                    f"{replied_user.first_name} is AFK ({minutes} minutes)\nReason: {reason}"
                )
            else:
                await update.message.reply_text(
                    f"{replied_user.first_name} is AFK ({minutes} minutes)"
                )

    # MENTION DETECTION
    if update.message.entities:

        text = update.message.text or ""

        for entity in update.message.entities:

            if entity.type == "mention":

                mention = text[entity.offset: entity.offset + entity.length]

                for uid in afk_users:

                    member = await context.bot.get_chat_member(
                        update.effective_chat.id,
                        uid
                    )

                    if member.user.username and mention == f"@{member.user.username}":

                        afk_data = afk_users[uid]
                        reason = afk_data["reason"]
                        afk_time = afk_data["time"]

                        duration = datetime.now() - afk_time
                        minutes = int(duration.total_seconds() / 60)

                        if reason:
                            await update.message.reply_text(
                                f"{member.user.first_name} is AFK ({minutes} minutes)\nReason: {reason}"
                            )
                        else:
                            await update.message.reply_text(
                                f"{member.user.first_name} is AFK ({minutes} minutes)"
                            )


# REGISTER HANDLERS
def register_afk(app):

    app.add_handler(CommandHandler("afk", afk), group=0)

    app.add_handler(
        MessageHandler(filters.ALL, check_afk),
        group=1
    )
