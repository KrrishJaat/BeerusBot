import json
import os
import asyncio
import time

from telegram import Update, ChatPermissions
from telegram.ext import CommandHandler, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from modules.filters import allow_in_dm
from telegram.helpers import mention_html
from modules.adminlogs import send_log

from config import OWNER_ID

RULES_FILE = "data/rules.json"
TPIN_FILE = "data/temp_pins.json"

if os.path.exists(TPIN_FILE):
    with open(TPIN_FILE) as f:
        TEMP_PINS = json.load(f)
else:
    TEMP_PINS = {}

def save_temp_pins():
    with open(TPIN_FILE, "w") as f:
        json.dump(TEMP_PINS, f, indent=4)

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

#PIN
async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await allow_in_dm(update):
        return

    rank = ADMIN_RANKS.get(str(update.effective_user.id))
    chat_id = update.effective_chat.id

    member = await context.bot.get_chat_member(chat_id, update.effective_user.id)

    if rank not in ["owner","dev","sudo","support"] and member.status not in ["administrator","creator"]:
        await update.message.reply_text("You're not authorized.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to pin.")
        return

    message_id = update.message.reply_to_message.message_id

    silent = True
    if context.args and context.args[0].lower() == "loud":
        silent = False

    await context.bot.pin_chat_message(
        chat_id,
        message_id,
        disable_notification=silent
    )

#TPIN (Temporary Pin)
async def tpin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await allow_in_dm(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to message.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /tpin <time>")
        return

    seconds = parse_time(context.args[0])

    if not seconds:
        await update.message.reply_text("Invalid time format.")
        return

    chat_id = update.effective_chat.id
    message_id = update.message.reply_to_message.message_id

    await context.bot.pin_chat_message(chat_id, message_id)

    import time
    unpin_time = int(time.time()) + seconds

    TEMP_PINS.setdefault(str(chat_id), {})
    TEMP_PINS[str(chat_id)][str(message_id)] = unpin_time
    save_temp_pins()

    await update.message.reply_text(f"Pinned for {context.args[0]}.")

async def check_temp_pins(context: ContextTypes.DEFAULT_TYPE):

    import time
    now = int(time.time())

    for chat_id in list(TEMP_PINS.keys()):
        for msg_id, until in list(TEMP_PINS[chat_id].items()):

            if now >= until:
                try:
                    await context.bot.unpin_chat_message(
                        int(chat_id),
                        int(msg_id)
                    )
                except:
                    pass

                del TEMP_PINS[chat_id][msg_id]

    save_temp_pins()

# CHAT LOCK
async def lock_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await allow_in_dm(update):
        return

    
    rank = ADMIN_RANKS.get(str(update.effective_user.id))
    chat_id = update.effective_chat.id

    member = await context.bot.get_chat_member(chat_id, update.effective_user.id)

    # allow if ranked OR admin
    if rank not in ["owner", "dev", "sudo", "support"] and member.status not in ["administrator", "creator"]:
        await update.message.reply_text("You're not authorized to use this command.")
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

    
    rank = ADMIN_RANKS.get(str(update.effective_user.id))
    chat_id = update.effective_chat.id

    member = await context.bot.get_chat_member(chat_id, update.effective_user.id)

    # allow if ranked OR admin
    if rank not in ["owner", "dev", "sudo", "support"] and member.status not in ["administrator", "creator"]:
        await update.message.reply_text("You're not authorized to use this command.")
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

    
    rank = ADMIN_RANKS.get(str(update.effective_user.id))
    chat_id = update.effective_chat.id

    member = await context.bot.get_chat_member(chat_id, update.effective_user.id)

    # allow if ranked OR admin
    if rank not in ["owner", "dev", "sudo", "support"] and member.status not in ["administrator", "creator"]:
        await update.message.reply_text("You're not authorized to use this command.")
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
        await update.message.reply_text("bitch you're not worthy")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "Reply to a user with:/grant <rank>"
        )
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /grant <rank>"
        )
        return

    rank = context.args[0].lower()
    tag = rank.upper()

    if rank not in RANK_LEVEL:
        await update.message.reply_text("Invalid rank.")
        return

    target = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id

    # OWNER PROTECTION
    if target.id == OWNER_ID:
        await update.message.reply_text("Using Command On Owner🤡")
        return

    # already rank holder
    target_rank = ADMIN_RANKS.get(str(target.id))
    if target_rank:
        await update.message.reply_text(
            f"This user is already a {target_rank.upper()}."
        )
        return

    # dev restrictions
    if actor_rank == "dev" and rank in ["owner", "dev"]:
        await update.message.reply_text("Dev cannot grant owner/dev rank.")
        return

    permissions = get_permissions(rank)

    member = await context.bot.get_chat_member(chat_id, target.id)

    # ALWAYS assign rank (this is your core system)
    ADMIN_RANKS[str(target.id)] = rank
    save_admin_ranks()

    # If NOT admin → promote
    if member.status not in ["administrator", "creator"]:
        try:
            await context.bot.promote_chat_member(
                chat_id,
                target.id,
                **permissions
            )
        except Exception as e:
            print("Promote failed:", e)

    # Try setting title (optional, never fail)
    try:
        await context.bot.set_chat_administrator_custom_title(
            chat_id,
            target.id,
            tag
        )
    except Exception as e:
        print("Title failed:", e)

    name = f"@{target.username}" if target.username else target.first_name
    user_mention = mention_html(target.id, name)

    await update.message.reply_text(
        f"⚡ {user_mention} has been granted <b>{rank.upper()}</b> rank.",
        parse_mode="HTML"
        )

# REVOKE RANK
async def revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):

    actor = update.effective_user
    actor_rank = ADMIN_RANKS.get(str(actor.id))

    if not await allow_in_dm(update):
        return

    if actor_rank not in ["owner", "dev"]:
        await update.message.reply_text("bitch you're not worthy")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to an admin to revoke rank.")
        return

    target = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id

    # OWNER PROTECTION
    if target.id == OWNER_ID:
        await update.message.reply_text("abe chutiye owner ko revoke karega? 🤡")
        return

    target_rank = ADMIN_RANKS.get(str(target.id))

    if not target_rank:
        await update.message.reply_text("This user has no rank to revoke.")
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

    except Exception as e:
        print(e)
        await update.message.reply_text("Failed to revoke rank.")

# ADMINS LIST
async def admins(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await allow_in_dm(update):
        return

    chat_id = update.effective_chat.id

    admins = await context.bot.get_chat_administrators(chat_id)

    text = "<b>Group Administrators</b>\n\n"

    for admin in admins:
        user = admin.user

        name = f"@{user.username}" if user.username else user.first_name
        mention = mention_html(user.id, name)

        status = "👑 Owner" if admin.status == "creator" else "🛡 Admin"

        text += f"{status} → {mention}\n"

    await update.message.reply_text(
        text,
        parse_mode="HTML"
    )

#RANKS
async def ranks(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await allow_in_dm(update):
        return

    if not ADMIN_RANKS:
        await update.message.reply_text("No ranks assigned.")
        return

    chat_id = update.effective_chat.id

    grouped = {
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
            mention = mention_html(user.id, name)

        except:
            mention = f"<code>{user_id}</code>"

        if rank in grouped:
            grouped[rank].append(mention)

    text = "⚡ <b>Bot Rank System</b>\n\n"

    if grouped["owner"]:
        text += "👑 Owner\n" + "\n".join(grouped["owner"]) + "\n\n"

    if grouped["dev"]:
        text += "⚡ Dev\n" + "\n".join(grouped["dev"]) + "\n\n"

    if grouped["sudo"]:
        text += "🛡 Sudo\n" + "\n".join(grouped["sudo"]) + "\n\n"

    if grouped["support"]:
        text += "🔰 Support\n" + "\n".join(grouped["support"]) + "\n\n"

    await update.message.reply_text(
        text.strip(),
        parse_mode="HTML"
    )

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
    app.add_handler(CommandHandler("ranks", ranks), group=0)
    app.add_handler(CommandHandler("pin", pin), group=0)
    app.add_handler(CommandHandler("tpin", tpin), group=0)
    app.job_queue.run_repeating(check_temp_pins, interval=30)