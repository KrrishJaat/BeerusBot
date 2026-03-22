import json
import os

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters
from modules.filters import allow_in_dm
from modules.adminlogs import send_log

from config import OWNER_ID
from modules.moderation import ADMIN_RANKS
from modules.groups import GROUPS


HAKAI_FILE = "data/hakai_bans.json"


# LOAD DATA
if os.path.exists(HAKAI_FILE):
    with open(HAKAI_FILE) as f:
        data = json.load(f)

        if isinstance(data, dict):
            HAKAI_BANS = data
        elif isinstance(data, list):
            # migrate old format
            HAKAI_BANS = {str(uid): "No reason recorded" for uid in data}
        else:
            HAKAI_BANS = {}
else:
    HAKAI_BANS = {}


def save_hakai():
    with open(HAKAI_FILE, "w") as f:
        json.dump(HAKAI_BANS, f, indent=4)


async def get_target(update, context):

    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user

    if context.args:
        username = context.args[0].replace("@", "")
        chat = update.effective_chat

        try:
            member = await context.bot.get_chat_member(chat.id, username)
            return member.user
        except:
            return None

    return None


def actor_rank(user_id):
    data = ADMIN_RANKS.get(str(user_id))
    return data if isinstance(data, str) else data.get("rank")


# GLOBAL BAN
async def hakai(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rank = actor_rank(update.effective_user.id)

    if rank not in ["owner", "dev"]:
        await update.message.reply_text("You're not worthy.")
        return

    if len(context.args) < 2 and not update.message.reply_to_message:
        await update.message.reply_text(
            "Usage:\n"
            "/hakai @user <reason>\n"
            "Reason is mandatory."
        )
        return

    target = await get_target(update, context)

    if not target:
        await update.message.reply_text("User not found.")
        return

    # GET REASON
    reason = " ".join(context.args[1:]) if not update.message.reply_to_message else " ".join(context.args)

    if not reason:
        await update.message.reply_text("Reason is mandatory.")
        return

    banned = 0

    for gid in GROUPS:

        try:
            member = await context.bot.get_chat_member(gid, context.bot.id)

            if member.can_restrict_members:
                await context.bot.ban_chat_member(gid, target.id)
                banned += 1

        except:
            pass

    # SAVE GLOBAL BAN
    HAKAI_BANS[str(target.id)] = reason
    save_hakai()

    await update.message.reply_text(
        f"☠ Hakai executed\n"
        f"User: {target.first_name}\n"
        f"Reason: {reason}\n"
        f"Banned in {banned} groups."
    )

    await send_log(
    context,
    update.effective_chat.id,
    f"☠ Hakai executed\nUser: {target.first_name}\nAdmin: {update.effective_user.first_name}\nReason: {reason}"
)


# GLOBAL UNBAN
async def unhakai(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rank = actor_rank(update.effective_user.id)

    if rank not in ["owner", "dev"]:
        await update.message.reply_text("You're not worthy.")
        return

    target = await get_target(update, context)

    if not target:
        await update.message.reply_text("User not found.")
        return

    unbanned = 0

    for gid in GROUPS:

        try:
            bot_member = await context.bot.get_chat_member(gid, context.bot.id)

            if bot_member.status in ["administrator", "creator"] and bot_member.can_restrict_members:

                await context.bot.unban_chat_member(gid, target.id)
                unbanned += 1

        except:
            pass

    if str(target.id) in HAKAI_BANS:
        del HAKAI_BANS[str(target.id)]
        save_hakai()

    await update.message.reply_text(
        f"🌌 Hakai reversed\nUser unbanned in {unbanned} groups."
    )

    await send_log(
    context,
    update.effective_chat.id,
    f"🌌 Hakai reversed\nUser: {target.first_name}\nAdmin: {update.effective_user.first_name}"
)


# HAKAI LIST
async def hakai_list(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not HAKAI_BANS:
        await update.message.reply_text("No globally banned users.")
        return

    text = "☠ Globally Banned Users\n\n"

    for uid, reason in HAKAI_BANS.items():
        text += f"{uid} — {reason}\n"

    await update.message.reply_text(text)


# LOCAL BAN
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rank = actor_rank(update.effective_user.id)

    if not await allow_in_dm(update):
        return

    if rank not in ["owner", "dev", "sudo", "support"]:
        await update.message.reply_text("You're not worthy.")
        return

    target = await get_target(update, context)

    if not target:
        await update.message.reply_text("User not found.")
        return

    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)

        await update.message.reply_text(
        f"{target.first_name} banned."
        )

    except Exception:
        await update.message.reply_text(
        "I cannot ban this user (maybe they are admin)."
        )


# LOCAL UNBAN
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rank = actor_rank(update.effective_user.id)

    if not await allow_in_dm(update):
        return

    if rank not in ["owner", "dev", "sudo", "support"]:
        await update.message.reply_text("You're not worthy.")
        return

    target = await get_target(update, context)

    if not target:
        await update.message.reply_text("User not found.")
        return

    await context.bot.unban_chat_member(update.effective_chat.id, target.id)

    await update.message.reply_text(
        f"{target.first_name} unbanned."
    )


# DELETE + BAN
async def dban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rank = actor_rank(update.effective_user.id)

    if rank not in ["owner", "dev", "sudo", "support"]:
        await update.message.reply_text("You're not worthy.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to message.")
        return

    target = update.message.reply_to_message.from_user

    try:
        await update.message.reply_to_message.delete()
    except:
        pass

    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
    except:
        await update.message.reply_text("Cannot ban this user.")
        return

    await update.message.reply_text(
        f"{target.first_name} banned."
    )


# AUTO GLOBAL BAN ON JOIN
async def auto_hakai_join(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message.new_chat_members:
        return

    for user in update.message.new_chat_members:

        if str(user.id) in HAKAI_BANS:

            try:
                await context.bot.ban_chat_member(
                    update.effective_chat.id,
                    user.id
                )
            except:
                pass


# AUTO GLOBAL BAN ON MESSAGE
async def auto_hakai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if str(user.id) in HAKAI_BANS:

        try:
            await context.bot.ban_chat_member(
                update.effective_chat.id,
                user.id
            )
        except:
            pass


def register_hakai(app):

    app.add_handler(CommandHandler("hakai", hakai), group=0)
    app.add_handler(CommandHandler("unhakai", unhakai), group=0)
    app.add_handler(CommandHandler("hakai_list", hakai_list), group=0)

    app.add_handler(CommandHandler("ban", ban), group=0)
    app.add_handler(CommandHandler("unban", unban), group=0)
    app.add_handler(CommandHandler("dban", dban), group=0)

    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, auto_hakai_join),
        group=0
    )

    app.add_handler(
        MessageHandler(filters.ALL & (~filters.COMMAND), auto_hakai_message),
        group=0
    )