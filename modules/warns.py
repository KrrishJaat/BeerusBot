from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler

from modules.moderation import is_admin
from utils import load_json, save_json
from modules.adminlogs import send_log


warn_file = "data/warns.json"
warns_db = load_json(warn_file)


def save_warns():
    save_json(warn_file, warns_db)


# WARN
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        await update.message.reply_text("Bitch You're Not Worthy.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to warn.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Reason required.")
        return

    reason = " ".join(context.args)

    user = update.message.reply_to_message.from_user
    chat_id = str(update.effective_chat.id)

    # Check if user still in group
    member = await context.bot.get_chat_member(update.effective_chat.id, user.id)

    if member.status in ["left", "kicked"]:
        await update.message.reply_text("User is no longer in this group.")
        return

    # prevent warning bot
    if user.id == context.bot.id:
        await update.message.reply_text("You Wanna Some Hakai?")
        return

    # prevent warning admins
    if member.status in ["administrator", "creator"]:
        await update.message.reply_text("Admins can't be warned.")
        return

    username = user.username if user.username else user.first_name

    if chat_id not in warns_db:
        warns_db[chat_id] = {}

    if str(user.id) not in warns_db[chat_id]:
        warns_db[chat_id][str(user.id)] = {
            "count": 0,
            "reasons": [],
            "username": username
        }

    warns_db[chat_id][str(user.id)]["count"] += 1
    warns_db[chat_id][str(user.id)]["reasons"].append(reason)

    count = warns_db[chat_id][str(user.id)]["count"]

    save_warns()

    # AUTO BAN
    if count >= 3:

        await context.bot.ban_chat_member(update.effective_chat.id, user.id)

        await update.message.reply_text(
            f"{user.first_name} reached 3 warns and has been banned."
        )

        await send_log(
            context,
            update.effective_chat.id,
            f"🔨 User banned (3 warns)\nUser: {user.first_name}\nAdmin: {update.effective_user.first_name}"
        )

        del warns_db[chat_id][str(user.id)]
        save_warns()
        return

    # REMOVE WARN BUTTON
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "❌ Remove Warn",
                callback_data=f"unwarn_{user.id}"
            )
        ]
    ])

    await update.message.reply_text(
        f"{user.first_name} warned.\nWarns: {count}/3\nReason: {reason}",
        reply_markup=keyboard
    )

    # LOG WARN
    await send_log(
        context,
        update.effective_chat.id,
        f"⚠ User warned\nUser: {user.first_name}\nAdmin: {update.effective_user.first_name}\nReason: {reason}"
    )


# BUTTON REMOVE WARN
async def unwarn_button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    admin = update.effective_user
    admin_name = admin.first_name

    if not await is_admin(update, context):
        await query.answer("Admins only.", show_alert=True)
        return

    data = query.data.split("_")
    user_id = data[1]

    chat_id = str(query.message.chat.id)

    if chat_id in warns_db and user_id in warns_db[chat_id]:

        warns_db[chat_id][user_id]["count"] -= 1

        if warns_db[chat_id][user_id]["count"] <= 0:
            del warns_db[chat_id][user_id]

        save_warns()

        await query.edit_message_text(
            f"⚠ Warn removed by {admin_name}"
        )

        await send_log(
            context,
            query.message.chat.id,
            f"⚠ Warn removed\nAdmin: {admin_name}"
        )

    else:
        await query.answer("User has no warns.", show_alert=True)


# DELETE WARN /DWARN
async def dwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        await update.message.reply_text("Bitch You're Not Worthy.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to warn.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Reason required.")
        return

    await warn(update, context)

    try:
        await update.message.reply_to_message.delete()
    except:
        pass


# UNWARN COMMAND
async def unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        await update.message.reply_text("Bitch You're Not Worthy.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user.")
        return

    user = update.message.reply_to_message.from_user
    chat_id = str(update.effective_chat.id)

    if chat_id in warns_db and str(user.id) in warns_db[chat_id]:

        data = warns_db[chat_id][str(user.id)]

        if data["count"] > 0:
            data["count"] -= 1

        if data["count"] <= 0:
            del warns_db[chat_id][str(user.id)]

        save_warns()

        await update.message.reply_text("Warn removed.")

        await send_log(
            context,
            update.effective_chat.id,
            f"⚠ Warn removed\nAdmin: {update.effective_user.first_name}"
        )

    else:
        await update.message.reply_text("User has no warns.")


# RESET WARN
async def resetwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    chat_id = str(update.effective_chat.id)

    if update.message.reply_to_message:

        user = update.message.reply_to_message.from_user

        if chat_id in warns_db and str(user.id) in warns_db[chat_id]:

            del warns_db[chat_id][str(user.id)]
            save_warns()

            await update.message.reply_text("Warns reset.")


# CHECK WARNS
async def warns(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = str(update.effective_chat.id)

    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    else:
        user = update.effective_user

    if chat_id in warns_db and str(user.id) in warns_db[chat_id]:

        data = warns_db[chat_id][str(user.id)]

        text = f"Warns for {user.first_name}\n\n"
        text += f"Total: {data['count']}/3\n\n"

        for i, r in enumerate(data["reasons"], start=1):
            text += f"{i}. {r}\n"

        await update.message.reply_text(text)

    else:
        await update.message.reply_text("No warns.")


# REGISTER HANDLERS
def register_warns(app):

    app.add_handler(CommandHandler("warn", warn), group=0)
    app.add_handler(CommandHandler("dwarn", dwarn), group=0)
    app.add_handler(CommandHandler("unwarn", unwarn), group=0)
    app.add_handler(CommandHandler("resetwarn", resetwarn), group=0)
    app.add_handler(CommandHandler("warns", warns), group=0)

    app.add_handler(
        CallbackQueryHandler(unwarn_button, pattern="^unwarn_")
    )