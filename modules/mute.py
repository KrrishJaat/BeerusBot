import json
import os
import time

from telegram import Update, ChatPermissions
from telegram.ext import CommandHandler, ContextTypes
from modules.adminlogs import send_log

from modules.moderation import ADMIN_RANKS, RANK_LEVEL


MUTE_FILE = "data/mutes.json"


if os.path.exists(MUTE_FILE):
    with open(MUTE_FILE) as f:
        MUTES = json.load(f)
else:
    MUTES = {}


def save_mutes():
    with open(MUTE_FILE, "w") as f:
        json.dump(MUTES, f, indent=4)


def actor_rank(user_id):
    data = ADMIN_RANKS.get(str(user_id))
    return data if isinstance(data, str) else data.get("rank")


def parse_time(text):

    if text.endswith("m"):
        return int(text[:-1]) * 60

    if text.endswith("h"):
        return int(text[:-1]) * 3600

    if text.endswith("d"):
        return int(text[:-1]) * 86400

    return None


# MUTE
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):

    
    rank = actor_rank(update.effective_user.id)
    chat_id_int = update.effective_chat.id

    member = await context.bot.get_chat_member(chat_id_int, update.effective_user.id)
    bot_member = await context.bot.get_chat_member(chat_id_int, context.bot.id)

    if not bot_member.can_restrict_members:
        await update.message.reply_text("I don't have permission to mute users.")
        return

    if rank not in ["owner", "dev", "sudo", "support"] and member.status not in ["administrator", "creator"]:
        await update.message.reply_text("You're not authorized to use this command.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to mute.")
        return


    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to mute.")
        return

    target = update.message.reply_to_message.from_user

    target_rank = actor_rank(target.id)

    if target_rank:
        actor_level = RANK_LEVEL.get(rank, 0)
        target_level = RANK_LEVEL.get(target_rank, 0)

        if target_level >= actor_level:
            await update.message.reply_text("You can't mute someone with equal or higher rank.")
            return

    chat_id = str(update.effective_chat.id)

    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        target.id,
        permissions=ChatPermissions(can_send_messages=False)
    )

    MUTES.setdefault(chat_id, {})
    MUTES[chat_id][str(target.id)] = 0

    save_mutes()

    await update.message.reply_text(f"{target.first_name} muted.")

    await send_log(
    context,
    update.effective_chat.id,
    f"🔇 User muted\nUser: {target.first_name}\nAdmin: {update.effective_user.first_name}"
)


# TEMP MUTE
async def tmute(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rank = actor_rank(update.effective_user.id)

    if rank not in ["owner", "dev", "sudo", "support"]:
        await update.message.reply_text("You're not worthy.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /tmute 10m")
        return

    seconds = parse_time(context.args[0])

    if not seconds:
        await update.message.reply_text("Invalid time.")
        return

    target = update.message.reply_to_message.from_user

    target_rank = actor_rank(target.id)

    if target_rank:
        actor_level = RANK_LEVEL.get(rank, 0)
        target_level = RANK_LEVEL.get(target_rank, 0)

        if target_level >= actor_level:
            await update.message.reply_text("You can't mute someone with equal or higher rank.")
            return

    chat_id = str(update.effective_chat.id)

    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        target.id,
        permissions=ChatPermissions(can_send_messages=False)
    )

    unmute_time = int(time.time()) + seconds

    MUTES.setdefault(chat_id, {})
    MUTES[chat_id][str(target.id)] = unmute_time

    save_mutes()

    await update.message.reply_text(
        f"{target.first_name} muted for {context.args[0]}."
    )

    await send_log(
    context,
    update.effective_chat.id,
    f"🔇 Temp mute\nUser: {target.first_name}\nAdmin: {update.effective_user.first_name}\nDuration: {context.args[0]}"
)


# UNMUTE
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rank = actor_rank(update.effective_user.id)

    if rank not in ["owner", "dev", "sudo", "support"]:
        await update.message.reply_text("You're not worthy.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to user.")
        return

    target = update.message.reply_to_message.from_user

    target_rank = actor_rank(target.id)

    if target_rank:
        actor_level = RANK_LEVEL.get(rank, 0)
        target_level = RANK_LEVEL.get(target_rank, 0)

        if target_level >= actor_level:
            await update.message.reply_text("You can't mute someone with equal or higher rank.")
            return

    chat_id = str(update.effective_chat.id)

    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        target.id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
    )

    if chat_id in MUTES and str(target.id) in MUTES[chat_id]:
        del MUTES[chat_id][str(target.id)]

    save_mutes()

    await update.message.reply_text(f"{target.first_name} unmuted.")

    await send_log(
    context,
    update.effective_chat.id,
    f"🔊 User unmuted\nUser: {target.first_name}\nAdmin: {update.effective_user.first_name}"
)


# AUTO UNMUTE CHECK
async def check_unmute(context: ContextTypes.DEFAULT_TYPE):

    now = int(time.time())

    for chat_id in list(MUTES.keys()):
        for user_id, until in list(MUTES[chat_id].items()):

            if until != 0 and now >= until:

                try:
                    await context.bot.restrict_chat_member(
                        int(chat_id),
                        int(user_id),
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True
                        )
                    )

                    del MUTES[chat_id][user_id]

                except:
                    pass

    save_mutes()


def register_mute(app):

    app.add_handler(CommandHandler("mute", mute), group=0)
    app.add_handler(CommandHandler("tmute", tmute), group=0)
    app.add_handler(CommandHandler("unmute", unmute), group=0)

    app.job_queue.run_repeating(check_unmute, interval=30)