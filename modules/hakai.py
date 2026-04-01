import json
import os

from telegram import Update
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.helpers import mention_html
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters
from modules.filters import allow_in_dm
from modules.adminlogs import send_log

from config import OWNER_ID
from modules.moderation import ADMIN_RANKS
from modules.groups import GROUPS

PAGE_SIZE = 15


def paginate(items, page):
    total = len(items)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    return items[start:end], total


def build_buttons(prefix, page, total):
    buttons = []

    if page > 0:
        buttons.append(InlineKeyboardButton("⬅ Prev", callback_data=f"{prefix}_{page-1}"))

    if (page + 1) * PAGE_SIZE < total:
        buttons.append(InlineKeyboardButton("Next ➡", callback_data=f"{prefix}_{page+1}"))

    return InlineKeyboardMarkup([buttons]) if buttons else None

HAKAI_FILE = "data/hakai_bans.json"
USER_FILE = "data/user_cache.json"
BAN_FILE = "data/local_bans.json"

if os.path.exists(BAN_FILE):
    with open(BAN_FILE) as f:
        LOCAL_BANS = json.load(f)
else:
    LOCAL_BANS = {}

def save_local_bans():
    with open(BAN_FILE, "w") as f:
        json.dump(LOCAL_BANS, f, indent=4)

if os.path.exists(USER_FILE):
    with open(USER_FILE) as f:
        USER_DB = json.load(f)
else:
    USER_DB = {}

TBAN_FILE = "data/temp_bans.json"

if os.path.exists(TBAN_FILE):
    with open(TBAN_FILE) as f:
        TEMP_BANS = json.load(f)
else:
    TEMP_BANS = {}

def save_temp_bans():
    with open(TBAN_FILE, "w") as f:
        json.dump(TEMP_BANS, f, indent=4)

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

def parse_time(text):
    text = text.lower()

    if text.endswith("min"):
        return int(text[:-3]) * 60
    if text.endswith("m"):
        return int(text[:-1]) * 60
    if text.endswith("h"):
        return int(text[:-1]) * 3600
    if text.endswith("d"):
        return int(text[:-1]) * 86400
    if text.endswith("w"):
        return int(text[:-1]) * 604800
    if text.endswith("mon"):
        return int(text[:-3]) * 2592000
    if text.endswith("y"):
        return int(text[:-1]) * 31536000

    return None

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
async def hakai_list(update, context):

    if not HAKAI_BANS:
        await update.message.reply_text("No global bans.")
        return

    items = list(HAKAI_BANS.items())
    await render_hakai_page(update, context, items, 0)


async def render_hakai_page(update, context, items, page):

    page_items, total = paginate(items, page)
    total_pages = (total - 1) // PAGE_SIZE + 1

    text = f"☠ <b>Hakai Panel</b>\n📄 Page {page+1}/{total_pages}\n\n"

    for uid, data in page_items:

        reason = data.get("reason", "No reason") if isinstance(data, dict) else data

        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, int(uid))
            user = member.user
            name = f"@{user.username}" if user.username else user.first_name
            mention = mention_html(user.id, name)
        except:
            mention = f"<code>{uid}</code>"

        text += f"👤 {mention}\n🚫 {reason}\n\n"

    keyboard = build_buttons("hakai", page, total)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def hakai_callback(update, context):
    query = update.callback_query
    await query.answer()

    page = int(query.data.split("_")[1])

    items = list(HAKAI_BANS.items())
    await render_hakai_page(update, context, items, page)
async def hakai_list(update, context):

    if not HAKAI_BANS:
        await update.message.reply_text("No global bans.")
        return

    items = list(HAKAI_BANS.items())
    await render_hakai_page(update, context, items, 0)


async def render_hakai_page(update, context, items, page):

    page_items, total = paginate(items, page)
    total_pages = (total - 1) // PAGE_SIZE + 1

    text = f"☠ <b>Hakai Panel</b>\n📄 Page {page+1}/{total_pages}\n\n"

    for uid, data in page_items:

        reason = data.get("reason", "No reason") if isinstance(data, dict) else data

        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, int(uid))
            user = member.user
            name = f"@{user.username}" if user.username else user.first_name
            mention = mention_html(user.id, name)
        except:
            mention = f"<code>{uid}</code>"

        text += f"👤 {mention}\n🚫 {reason}\n\n"

    keyboard = build_buttons("hakai", page, total)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def hakai_callback(update, context):
    query = update.callback_query
    await query.answer()

    page = int(query.data.split("_")[1])

    items = list(HAKAI_BANS.items())
    await render_hakai_page(update, context, items, page)


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

        # ✅ STORE BAN
        chat_str = str(chat_id)
        user_str = str(target.id)

        LOCAL_BANS.setdefault(chat_str, {})
        LOCAL_BANS[chat_str][user_str] = {
            "name": target.first_name,
            "admin": update.effective_user.first_name,
            "reason": "No reason"
        }

        save_local_bans()

        await update.message.reply_text(f"{target.first_name} banned.")

    except Exception as e:
        print(e)
        await update.message.reply_text("I cannot ban this user (maybe admin).")

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
    chat_str = str(chat_id)
    user_str = str(target.id)

    if chat_str in LOCAL_BANS and user_str in LOCAL_BANS[chat_str]:
        del LOCAL_BANS[chat_str][user_str]
        save_local_bans()
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

        chat_str = str(chat_id)
        user_str = str(target.id)

        LOCAL_BANS.setdefault(chat_str, {})
        LOCAL_BANS[chat_str][user_str] = {
            "name": target.first_name,
            "admin": update.effective_user.first_name,
            "reason": "Deleted + Ban"
        }

        save_local_bans()

    except Exception:
        await update.message.reply_text("Cannot ban this user.")
        return
        await update.message.reply_text("Cannot ban this user.")
        return

    except:
        await update.message.reply_text("Cannot ban this user.")
        return
    await update.message.reply_text(f"{target.first_name} banned.")

#BAN LIST
async def banlist(update, context):

    chat_id = str(update.effective_chat.id)

    if chat_id not in LOCAL_BANS or not LOCAL_BANS[chat_id]:
        await update.message.reply_text("No banned users.")
        return

    items = list(LOCAL_BANS[chat_id].items())
    await render_ban_page(update, context, items, 0)

async def render_ban_page(update, context, items, page):

    page_items, total = paginate(items, page)
    total_pages = (total - 1) // PAGE_SIZE + 1

    text = f"🚫 <b>Ban Panel</b>\n📄 Page {page+1}/{total_pages}\n\n"

    for user_id, data in page_items:

        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, int(user_id))
            user = member.user
            name = f"@{user.username}" if user.username else user.first_name
            mention = mention_html(user.id, name)
        except:
            mention = f"<code>{user_id}</code>"

        admin = data.get("admin", "Unknown")
        reason = data.get("reason", "No reason")

        text += f"👤 {mention}\n"
        text += f"🛡 By: {admin}\n"
        text += f"📌 {reason}\n\n"

    keyboard = build_buttons("ban", page, total)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)

#TBAN (Temporary Ban)
async def tban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rank = actor_rank(update.effective_user.id)

    chat_id = update.effective_chat.id
    member = await context.bot.get_chat_member(chat_id, update.effective_user.id)

    if rank not in ["owner","dev","sudo","support"] and member.status not in ["administrator","creator"]:
        await update.message.reply_text("You're not authorized.")
        return

    # reply method
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user

        if not context.args:
            await update.message.reply_text("Usage: /tban <time>")
            return

        time_arg = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason"

    else:
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /tban <user> <time>")
            return

        username = context.args[0].replace("@","")
        time_arg = context.args[1]
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else "No reason"

        try:
            member = await context.bot.get_chat_member(chat_id, username)
            target = member.user
        except:
            await update.message.reply_text("User not found.")
            return

    seconds = parse_time(time_arg)

    if not seconds:
        await update.message.reply_text("Invalid time.")
        return

    import time
    unban_time = int(time.time()) + seconds

    TEMP_BANS.setdefault(str(chat_id), {})
    TEMP_BANS[str(chat_id)][str(target.id)] = unban_time
    save_temp_bans()

    await context.bot.ban_chat_member(chat_id, target.id)

    await update.message.reply_text(
        f"{target.first_name} banned for {time_arg}.\nReason: {reason}"
    )

async def check_temp_bans(context: ContextTypes.DEFAULT_TYPE):

    import time
    now = int(time.time())

    for chat_id in list(TEMP_BANS.keys()):
        for user_id, until in list(TEMP_BANS[chat_id].items()):

            if now >= until:
                try:
                    await context.bot.unban_chat_member(
                        int(chat_id),
                        int(user_id)
                    )
                except:
                    pass

                del TEMP_BANS[chat_id][user_id]

    save_temp_bans()

#TBAN LIST
async def tbanlist(update, context):

    if not TEMP_BANS:
        await update.message.reply_text("No active temp bans.")
        return

    items = []
    for chat_id, users in TEMP_BANS.items():
        for uid, until in users.items():
            items.append((chat_id, uid, until))

    await render_tban_page(update, context, items, 0)


async def render_tban_page(update, context, items, page):

    import time
    now = int(time.time())

    page_items, total = paginate(items, page)
    total_pages = (total - 1) // PAGE_SIZE + 1

    text = f"⏳ <b>Temp Ban Panel</b>\n📄 Page {page+1}/{total_pages}\n\n"

    for chat_id, user_id, until in page_items:

        remaining = max(0, (until - now) // 60)

        try:
            member = await context.bot.get_chat_member(int(chat_id), int(user_id))
            user = member.user
            name = f"@{user.username}" if user.username else user.first_name
            mention = mention_html(user.id, name)
        except:
            mention = f"<code>{user_id}</code>"

        text += f"👤 {mention} — ⏱ {remaining} min\n"

    keyboard = build_buttons("tban", page, total)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def ban_callback(update, context):
    query = update.callback_query
    await query.answer()

    page = int(query.data.split("_")[1])
    chat_id = str(query.message.chat.id)

    items = list(LOCAL_BANS.get(chat_id, {}).items())
    await render_ban_page(update, context, items, page)

# AUTO GLOBAL BAN ON JOIN
async def auto_hakai_join(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if not update.message.new_chat_members:
        return

    for user in update.message.new_chat_members:

        if str(user.id) in HAKAI_BANS or f"@{user.username}" in HAKAI_BANS:

            try:
                await context.bot.ban_chat_member(
                    update.effective_chat.id,
                    user.id
                )

                # optional clean message
                await update.message.reply_text(
                    "🚫 User removed (globally banned)."
                )

            except Exception as e:
                print("Join ban failed:", e)


# AUTO GLOBAL BAN ON MESSAGE
async def auto_hakai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    chat_id = update.effective_chat.id

    if not user:
        return

    if str(user.id) not in HAKAI_BANS and f"@{user.username}" not in HAKAI_BANS:
        return

    try:
        member = await context.bot.get_chat_member(chat_id, user.id)

        # avoid loop
        if member.status in ["kicked", "restricted"]:
            return

    except:
        return

    try:
        # delete message first (clean UX)
        if update.message:
            try:
                await update.message.delete()
            except:
                pass

        await context.bot.ban_chat_member(chat_id, user.id)

    except Exception as e:
        print("Message ban failed:", e)


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
    app.job_queue.run_repeating(check_temp_bans, interval=30)
    app.add_handler(MessageHandler(filters.ALL, cache_user), group=1)

    app.add_handler(CommandHandler("ban", ban), group=0)
    app.add_handler(CommandHandler("unban", unban), group=0)
    app.add_handler(CommandHandler("dban", dban), group=0)
    app.add_handler(CommandHandler("tbanlist", tbanlist))
    app.add_handler(CommandHandler("hakai_list", hakai_list))
    app.add_handler(CommandHandler("banlist", banlist), group=0)

    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, auto_hakai_join),
        group=0
    )

    app.add_handler(MessageHandler(filters.ALL, auto_hakai_message), group=0)
    app.add_handler(CallbackQueryHandler(tban_callback, pattern=r"^tban_"))
    app.add_handler(CallbackQueryHandler(hakai_callback, pattern=r"^hakai_"))
    app.add_handler(CallbackQueryHandler(ban_callback, pattern=r"^ban_"))


async def tban_callback(update, context):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_")[1])

    items = []
    for chat_id, users in TEMP_BANS.items():
        for uid, until in users.items():
            items.append((chat_id, uid, until))

    await render_tban_page(update, context, items, page)
