import json
import os

from telegram import Update
from telegram.helpers import mention_html
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters
from modules.filters import allow_in_dm
from modules.adminlogs import send_log

from config import OWNER_ID
from modules.moderation import ADMIN_RANKS
from modules.groups import GROUPS


HAKAI_FILE = "data/hakai_bans.json"
USER_FILE = "data/user_cache.json"

if os.path.exists(USER_FILE):
    with open(USER_FILE) as f:
        USER_DB = json.load(f)
else:
    USER_DB = {}

# LOAD DATA
if os.path.exists(HAKAI_FILE):
    with open(HAKAI_FILE) as f:
        data = json.load(f)

        if isinstance(data, dict):
            HAKAI_BANS = data
        elif isinstance(data, list):
            HAKAI_BANS = {str(uid): "No reason recorded" for uid in data}
        else:
            HAKAI_BANS = {}
else:
    HAKAI_BANS = {}


def save_hakai():
    with open(HAKAI_FILE, "w") as f:
        json.dump(HAKAI_BANS, f, indent=4)


def save_users():
    with open(USER_FILE, "w") as f:
        json.dump(USER_DB, f, indent=4)


async def get_target(update, context):

    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user

    if context.args:
        arg = context.args[0]

        if arg.isdigit():
            class FakeUser:
                def __init__(self, uid):
                    self.id = int(uid)
                    self.first_name = str(uid)
            return FakeUser(arg)

        if arg.startswith("@"):
            username = arg[1:].lower()

            if username in USER_DB:
                uid = USER_DB[username]

                class FakeUser:
                    def __init__(self, uid, username):
                        self.id = uid
                        self.first_name = username

                return FakeUser(uid, username)

            else:
                class FakeUser:
                    def __init__(self, username):
                        self.id = f"@{username}"
                        self.first_name = username

                return FakeUser(username)

    return None


def actor_rank(user_id):
    data = ADMIN_RANKS.get(str(user_id))
    return data if isinstance(data, str) else data.get("rank")


# GLOBAL BAN
async def hakai(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rank = actor_rank(update.effective_user.id)

    user = update.effective_user
    chat_id = update.effective_chat.id
    member = await context.bot.get_chat_member(chat_id, user.id)

    if rank not in ["owner", "dev"]:

        if member.status in ["administrator", "creator"]:
            await update.message.reply_text(
                "Oh wow, an admin using /hakai without permission 🤡\nKnow your level."
            )
        else:
            await update.message.reply_text(
                "Who even are you? 🤡 This command isn't meant for you."
            )

        return

    if len(context.args) < 2 and not update.message.reply_to_message:
        await update.message.reply_text(
            "Usage:\n"
            "/hakai @user <reason>\n"
            "Reason is mandatory."
        )
        return

    target = await get_target(update, context)

    # OWNER PROTECTION + RANK REMOVAL
    if target and target.id == OWNER_ID:

        actor = update.effective_user
        actor_id = str(actor.id)
        actor_rank_value = actor_rank(actor.id)

        member = await context.bot.get_chat_member(update.effective_chat.id, actor.id)

        if actor_rank_value in ["dev", "sudo", "support"]:

            if actor_id in ADMIN_RANKS:
                ADMIN_RANKS.pop(actor_id)

            await update.message.reply_text(
                "Hakai On Owner? 🤡 Rank Revoked, Now Go To Hell"
            )

        elif member.status in ["administrator", "creator"]:
            await update.message.reply_text(
                "Being admin doesn't make you god 🤡 Trying to hakai the OWNER?"
            )
        else:
            await update.message.reply_text(
                "Trying to hakai the OWNER? Keep dreaming 🤡"
            )

        return

    uid = str(target.id)

    if uid in HAKAI_BANS or (isinstance(target.id, str) and target.id in HAKAI_BANS):
        existing = HAKAI_BANS.get(uid) or HAKAI_BANS.get(target.id)

        reason_old = (
            existing.get("reason")
            if isinstance(existing, dict)
            else existing
        )

        await update.message.reply_text(
            f"⚠️ User already hakaid.\nReason: {reason_old}"
        )
        return

    if not target:
        await update.message.reply_text("User not found.")
        return

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

    uid = str(target.id)

    HAKAI_BANS[uid] = {
        "name": target.first_name,
        "reason": reason
    }

    if isinstance(target.id, str) and target.id.startswith("@"):
        HAKAI_BANS[target.id] = {
            "name": target.first_name,
            "reason": reason
        }

    save_hakai()

    # FIXED BLOCK
    if isinstance(target.id, int):
        if target.first_name.startswith("@"):
            user_mention = mention_html(target.id, target.first_name)
        else:
            user_mention = mention_html(target.id, f"@{target.first_name}")
    else:
        user_mention = target.first_name

    admin_mention = mention_html(update.effective_user.id, update.effective_user.first_name)

    await update.message.reply_text(
        f"☠ <b>Hakai Executed</b>\n"
        f"👤 User: {user_mention}\n"
        f"🛡 Admin: {admin_mention}\n"
        f"📌 Reason: {reason}\n"
        f"🚫 Banned in {banned} groups.",
        parse_mode="HTML"
    )

    await send_log(
        context,
        update.effective_chat.id,
        f"☠ <b>Hakai Executed</b>\n"
        f"👤 User: {user_mention}\n"
        f"🛡 Admin: {admin_mention}\n"
        f"📌 Reason: {reason}"
    )


# GLOBAL UNBAN
async def unhakai(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rank = actor_rank(update.effective_user.id)

    user = update.effective_user
    chat_id = update.effective_chat.id
    member = await context.bot.get_chat_member(chat_id, user.id)

    if rank not in ["owner", "dev"]:

        if member.status in ["administrator", "creator"]:
            await update.message.reply_text(
                "Oh wow, an admin using /hakai without permission 🤡\nKnow your level."
            )
        else:
            await update.message.reply_text(
                "Who even are you? 🤡 This command isn't meant for you."
            )

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

    uid = str(target.id)

    if uid in HAKAI_BANS:
        del HAKAI_BANS[uid]

    if isinstance(target.id, str) and target.id.startswith("@"):
        if target.id in HAKAI_BANS:
            del HAKAI_BANS[target.id]

    save_hakai()

    await update.message.reply_text(
        f"🌌 Hakai reversed\nUser unbanned in {unbanned} groups."
    )

    await send_log(
        context,
        update.effective_chat.id,
        f"🌌 <b>Hakai Reversed</b>\n"
        f"👤 User: {target.first_name}\n"
        f"🛡 Admin: {update.effective_user.first_name}"
    )


# HAKAI LIST
async def hakai_list(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not HAKAI_BANS:
        await update.message.reply_text("No globally banned users.")
        return

    text = "☠ Globally Banned Users\n\n"

    for uid, data in HAKAI_BANS.items():
        if isinstance(data, dict):
            name = data.get("name", uid)
            reason = data.get("reason", "No reason")
        else:
            name = uid
            reason = data

        text += f"• {name} ({uid})\n  └ {reason}\n\n"

    await update.message.reply_text(text)


# LOCAL BAN
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rank = actor_rank(update.effective_user.id)

    if not await allow_in_dm(update):
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    member = await context.bot.get_chat_member(chat_id, user_id)
    bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)

    if not bot_member.can_restrict_members:
        await update.message.reply_text("I don't have permission to ban users.")
        return

    if rank not in ["owner", "dev", "sudo", "support"] and member.status not in ["administrator", "creator"]:
        await update.message.reply_text("You're not authorized to use this command.")
        return

    target = await get_target(update, context)

    if not target:
        await update.message.reply_text("User not found.")
        return

    target_rank = actor_rank(target.id)

    if target.id == OWNER_ID:
        await update.message.reply_text("You really thought you could ban the owner? 🤡")
        return

    if target_rank:
        actor_level = RANK_LEVEL.get(rank, 0)
        target_level = RANK_LEVEL.get(target_rank, 0)
        if target_level >= actor_level:
            await update.message.reply_text("You can't ban someone with equal or higher rank.")
            return

    try:
        await context.bot.ban_chat_member(chat_id, target.id)
        await update.message.reply_text(f"{target.first_name} banned.")
    except Exception:
        await update.message.reply_text("I cannot ban this user (maybe they are admin).")


# LOCAL UNBAN
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rank = actor_rank(update.effective_user.id)

    if not await allow_in_dm(update):
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    member = await context.bot.get_chat_member(chat_id, user_id)

    if rank not in ["owner", "dev", "sudo", "support"] and member.status not in ["administrator", "creator"]:
        await update.message.reply_text("You're not authorized to use this command.")
        return

    target = await get_target(update, context)

    if not target:
        await update.message.reply_text("User not found.")
        return

    await context.bot.unban_chat_member(chat_id, target.id)
    await update.message.reply_text(f"{target.first_name} unbanned.")



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

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    member = await context.bot.get_chat_member(chat_id, user_id)
    bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)

    if rank not in ["owner", "dev", "sudo", "support"] and member.status not in ["administrator", "creator"]:
        await update.message.reply_text("You're not authorized to use this command.")
        return

    if not bot_member.can_restrict_members:
        await update.message.reply_text("I don't have permission to ban users.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to message.")
        return

    target = update.message.reply_to_message.from_user

    target_rank = actor_rank(target.id)

    if target.id == OWNER_ID:
        await update.message.reply_text("You really thought you could ban the owner? 🤡")
        return

    if target_rank:
        actor_level = RANK_LEVEL.get(rank, 0)
        target_level = RANK_LEVEL.get(target_rank, 0)
        if target_level >= actor_level:
            await update.message.reply_text("You can't ban someone with equal or higher rank.")
            return

    try:
        await update.message.reply_to_message.delete()
    except:
        pass

    try:
        await context.bot.ban_chat_member(chat_id, target.id)
    except:
        await update.message.reply_text("Cannot ban this user.")
        return

    await update.message.reply_text(f"{target.first_name} banned.")


# AUTO GLOBAL BAN ON JOIN
async def auto_hakai_join(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message.new_chat_members:
        return

    for user in update.message.new_chat_members:

        if str(user.id) in HAKAI_BANS or f"@{user.username}" in HAKAI_BANS:

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

    if str(user.id) in HAKAI_BANS or f"@{user.username}" in HAKAI_BANS:

        try:
            await context.bot.ban_chat_member(
                update.effective_chat.id,
                user.id
            )
        except:
            pass


async def cache_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user:
        return

    if user.username:
        USER_DB[user.username.lower()] = user.id
        save_users()


def register_hakai(app):

    app.add_handler(CommandHandler("hakai", hakai), group=0)
    app.add_handler(CommandHandler("unhakai", unhakai), group=0)
    app.add_handler(CommandHandler("hakai_list", hakai_list), group=0)
    app.add_handler(MessageHandler(filters.ALL, cache_user), group=1)

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
