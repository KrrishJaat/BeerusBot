import json
import os
import asyncio
import time

from telegram import Update, ChatPermissions
from telegram.ext import CommandHandler, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from modules.filters import allow_in_dm
from modules.adminlogs import send_log

from config import OWNER_ID

RULES_FILE = "data/rules.json"

if os.path.exists(RULES_FILE):
    with open(RULES_FILE, "r") as f:
        RULES_DB = json.load(f)
else:
    RULES_DB = {}


def save_rules():
    with open(RULES_FILE, "w") as f:
        json.dump(RULES_DB, f, indent=4)

# ADMIN RANK STORAGE
ADMIN_RANK_FILE = "data/admin_ranks.json"

if os.path.exists(ADMIN_RANK_FILE):
    with open(ADMIN_RANK_FILE, "r") as f:
        ADMIN_RANKS = json.load(f)
else:
    ADMIN_RANKS = {}


def save_admin_ranks():
    with open(ADMIN_RANK_FILE, "w") as f:
        json.dump(ADMIN_RANKS, f)


# Ensure bot owner exists
if str(OWNER_ID) not in ADMIN_RANKS:
    ADMIN_RANKS[str(OWNER_ID)] = "owner"
    save_admin_ranks()


# ADMIN CHECK (group admin)
async def is_admin(update, context):

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id == OWNER_ID:
        return True

    member = await context.bot.get_chat_member(chat_id, user_id)

    return member.status in ["administrator", "creator"]


# RANK HIERARCHY
RANK_LEVEL = {
    "owner": 4,
    "dev": 3,
    "sudo": 2,
    "support": 1
}


# PERMISSIONS FOR TELEGRAM ADMIN
def get_permissions(rank):

    if rank == "owner":
        return dict(
            can_change_info=True,
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_promote_members=True,
            can_manage_chat=True
        )

    if rank == "dev":
        return dict(
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_promote_members=True,
            can_manage_chat=True
        )

    if rank == "sudo":
        return dict(
            can_delete_messages=True,
            can_restrict_members=True,
            can_promote_members=True,
            can_invite_users=True,
            can_pin_messages=True
        )

    if rank == "support":
        return dict(
            can_delete_messages=True,
            can_restrict_members=True
        )

    return {}


# PING
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = time.time()

    msg = await update.message.reply_text("🏓 Checking...")

    latency = (time.time() - start) * 1000

    await msg.edit_text(
        f"🏓 <b>Pong!</b>\n"
        f"⚡ <b>Latency:</b> {latency:.2f} ms",
        parse_mode="HTML"
    )


# CHAT LOCK
async def lock_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await allow_in_dm(update):
        return

    if not await is_admin(update, context):
        await update.message.reply_text("You're not worthy.")
        return

    chat_id = update.effective_chat.id

    await context.bot.set_chat_permissions(
        chat_id,
        ChatPermissions(can_send_messages=False)
    )

    await update.message.reply_text(
        "🔒 Chat Locked\nOnly admins can talk now."
    )


# CHAT UNLOCK
async def unlock_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await allow_in_dm(update):
        return

    if not await is_admin(update, context):
        await update.message.reply_text("You're not worthy.")
        return

    chat_id = update.effective_chat.id

    await context.bot.set_chat_permissions(
        chat_id,
        ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
    )

    await update.message.reply_text(
        "🔓 Chat Unlocked\nEveryone can talk now."
    )


# FAST PURGE
async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await allow_in_dm(update):
        return

    if not await is_admin(update, context):
        await update.message.reply_text("You're not worthy.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to purge.")
        return

    start_id = update.message.reply_to_message.message_id
    end_id = update.message.message_id
    chat_id = update.effective_chat.id

    tasks = []

    for msg_id in range(start_id, end_id + 1):
        tasks.append(context.bot.delete_message(chat_id, msg_id))

    await asyncio.gather(*tasks, return_exceptions=True)


# GRANT RANK
async def grant(update: Update, context: ContextTypes.DEFAULT_TYPE):

    actor = update.effective_user
    actor_rank = ADMIN_RANKS.get(str(actor.id))

    if not await allow_in_dm(update):
        return

    if actor_rank not in ["owner", "dev"]:
        await update.message.reply_text("Only Owner or Dev can grant ranks.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "Reply to a user with:\n/grant <rank> <title>"
        )
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /grant <rank> <title>"
        )
        return

    rank = context.args[0].lower()
    tag = context.args[1]

    if rank not in RANK_LEVEL:
        await update.message.reply_text("Invalid rank.")
        return

    target = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id

    # dev restrictions
    if actor_rank == "dev" and rank in ["owner", "dev"]:
        await update.message.reply_text("Dev cannot grant owner/dev rank.")
        return

    permissions = get_permissions(rank)

    try:

        await context.bot.promote_chat_member(
            chat_id,
            target.id,
            **permissions
        )

        await context.bot.set_chat_administrator_custom_title(
            chat_id,
            target.id,
            tag
        )

        ADMIN_RANKS[str(target.id)] = rank
        save_admin_ranks()

        await update.message.reply_text(
            f"{target.first_name} granted rank as {rank.upper()}."
        )

    except Exception as e:
        print(e)
        await update.message.reply_text("Failed to grant rank.")

        await send_log(
    context,
    update.effective_chat.id,
    f"⭐ Admin promoted\nUser: {target.first_name}\nAdmin: {update.effective_user.first_name}"
)


# REVOKE RANK
async def revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):

    actor = update.effective_user
    actor_rank = ADMIN_RANKS.get(str(actor.id))

    if not await allow_in_dm(update):
        return

    if actor_rank not in ["owner", "dev"]:
        await update.message.reply_text("Only Owner or Dev can revoke ranks.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to an admin to revoke rank.")
        return

    target = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id

    target_rank = ADMIN_RANKS.get(str(target.id))

    if not target_rank:
        await update.message.reply_text("This user has no bot rank.")
        return

    if actor_rank == "dev" and target_rank in ["owner", "dev"]:
        await update.message.reply_text(
            "Dev cannot revoke Owner/Dev rank."
        )
        return

    try:

        await context.bot.promote_chat_member(
            chat_id,
            target.id,
            can_change_info=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_chat=False
        )

        ADMIN_RANKS.pop(str(target.id), None)
        save_admin_ranks()

        await update.message.reply_text(
            f"{target.first_name}'s rank has been revoked."
        )

    except:
        await update.message.reply_text("Failed to revoke rank.")

        await send_log(
    context,
    update.effective_chat.id,
    f"⬇ Admin demoted\nUser: {target.first_name}\nAdmin: {update.effective_user.first_name}"
)


# ADMINS LIST
async def admins(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await allow_in_dm(update):
        return

    if not ADMIN_RANKS:
        await update.message.reply_text("No admins recorded.")
        return

    chat_id = update.effective_chat.id

    ranks = {
        "owner": [],
        "dev": [],
        "sudo": [],
        "support": []
    }

    for user_id, rank in ADMIN_RANKS.items():

        try:
            member = await context.bot.get_chat_member(chat_id, int(user_id))

            if member.status in ["left", "kicked"]:
                continue

            user = member.user
            name = f"@{user.username}" if user.username else user.first_name

        except:
            name = f"User({user_id})"

        if rank in ranks:
            ranks[rank].append(name)

    text = ""

    if ranks["owner"]:
        text += "👑 Owner\n"
        text += "\n".join(ranks["owner"]) + "\n\n"

    if ranks["dev"]:
        text += "⚡ Dev\n"
        text += "\n".join(ranks["dev"]) + "\n\n"

    if ranks["sudo"]:
        text += "🛡 Sudo\n"
        text += "\n".join(ranks["sudo"]) + "\n\n"

    if ranks["support"]:
        text += "🔰 Support\n"
        text += "\n".join(ranks["support"]) + "\n\n"

    await update.message.reply_text(text.strip())

# PROMOTE (group admin)
async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):

    actor = update.effective_user
    chat_id = update.effective_chat.id

    member = await context.bot.get_chat_member(chat_id, actor.id)

    if not await allow_in_dm(update):
        return

    if not member.can_promote_members:
        await update.message.reply_text("You don't have permission to promote admins.")
        return

    actor_rank = ADMIN_RANKS.get(str(actor.id))

    if actor_rank not in ["owner", "dev", "sudo"]:
        await update.message.reply_text("Your bot rank cannot promote admins.")
        return

    # reply usage
    if update.message.reply_to_message:

        target = update.message.reply_to_message.from_user

        if len(context.args) < 1:
            await update.message.reply_text("Usage: /promote <title>")
            return

        title = context.args[0]

    else:

        if len(context.args) < 2:
            await update.message.reply_text("Usage: /promote <username> <title>")
            return

        username = context.args[0].replace("@", "")
        title = context.args[1]

        try:
            member = await context.bot.get_chat_member(chat_id, username)
            target = member.user
        except:
            await update.message.reply_text("User not found.")
            return


    try:

        await context.bot.promote_chat_member(
            chat_id,
            target.id,
            can_delete_messages=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True
        )

        await context.bot.set_chat_administrator_custom_title(
            chat_id,
            target.id,
            title
        )

        await update.message.reply_text(
            f"{target.first_name} promoted as admin."
        )

    except:
        await update.message.reply_text("Promotion failed.")

# DEMOTE (group admin)
async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):

    actor = update.effective_user
    chat_id = update.effective_chat.id

    member = await context.bot.get_chat_member(chat_id, actor.id)

    if not await allow_in_dm(update):
        return

    if not member.can_promote_members:
        await update.message.reply_text("You don't have permission to demote admins.")
        return

    actor_rank = ADMIN_RANKS.get(str(actor.id))

    if actor_rank not in ["owner", "dev", "sudo"]:
        await update.message.reply_text("Your bot rank cannot demote admins.")
        return

    # reply usage
    if update.message.reply_to_message:

        target = update.message.reply_to_message.from_user

    else:

        if len(context.args) < 1:
            await update.message.reply_text("Reply to admin or use /demote <username>")
            return

        username = context.args[0].replace("@", "")

        try:
            member = await context.bot.get_chat_member(chat_id, username)
            target = member.user
        except:
            await update.message.reply_text("User not found.")
            return

    try:

        await context.bot.promote_chat_member(
            chat_id,
            target.id,
            can_change_info=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_chat=False
        )

        await update.message.reply_text(
            f"{target.first_name} demoted from admin."
        )

    except:
        await update.message.reply_text("Demotion failed.")

# SETRULES
async def setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await allow_in_dm(update):
        return

    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can set rules.")
        return

    chat = update.effective_chat
    chat_id = str(chat.id)

    text = " ".join(context.args)

    if not text:
        await update.message.reply_text(
            "Usage:\n/setrules <rules>"
        )
        return

    RULES_DB[chat_id] = {
        "rules": text,
        "title": chat.title
    }

    save_rules()

    await update.message.reply_text(
        f"Rules saved for {chat.title}"
    )

#RULES
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat

    # If command used in private chat
    if chat.type == "private":
        await update.message.reply_text(
            "Please use /rules inside a group to view that group's rules."
        )
        return

    chat_id = str(chat.id)

    if chat_id not in RULES_DB:
        await update.message.reply_text("Rules are not set for this group.")
        return

    link = f"https://t.me/{context.bot.username}?start=rules_{chat_id}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("View Rules", url=link)]
    ])

    await update.message.reply_text(
        "Click the button below to view the group rules.",
        reply_markup=keyboard
    )

# REGISTER COMMANDS
def register_moderation(app):

    app.add_handler(CommandHandler("lock", lock_chat), group=0)
    app.add_handler(CommandHandler("unlock", unlock_chat), group=0)
    app.add_handler(CommandHandler("ping", ping), group=0)
    app.add_handler(CommandHandler("purge", purge), group=0)
    app.add_handler(CommandHandler("grant", grant), group=0)
    app.add_handler(CommandHandler("revoke", revoke), group=0)
    app.add_handler(CommandHandler("admins", admins), group=0)
    app.add_handler(CommandHandler("promote", promote), group=0)
    app.add_handler(CommandHandler("demote", demote), group=0)
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("setrules", setrules))