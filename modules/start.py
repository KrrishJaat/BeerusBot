from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from modules.moderation import RULES_DB


# MAIN MENU KEYBOARD
def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Admin", callback_data="help_admin"),
            InlineKeyboardButton("Moderation", callback_data="help_mod")
        ],
        [
            InlineKeyboardButton("AFK", callback_data="help_afk"),
            InlineKeyboardButton("Hakai", callback_data="help_hakai")
        ],
        [
            InlineKeyboardButton("Notes", callback_data="help_notes"),
            InlineKeyboardButton("Warns", callback_data="help_warn")
        ],
        [
            InlineKeyboardButton("General", callback_data="help_general")
        ]
    ])


# MAIN MENU TEXT
def main_text():
    return (
        "Hello! I'm your very own group manager!\n\n"
        "I'm a modular group management bot with a few fun extras!\n"
        "Have a look at the following for an idea of some of the things I can help you with.\n\n"
        "Main commands available:\n"
        "• /start : Check if I'm alive.\n"
        "• /help : Open this help menu.\n\n"
        "Choose a category below."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        main_text(),
        reply_markup=main_keyboard()
    )

# START COMMAND
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # RULES REDIRECT
    if context.args and context.args[0].startswith("rules_"):

        chat_id = context.args[0].split("_")[1]

        if chat_id in RULES_DB:

            data = RULES_DB[chat_id]

            rules_text = data["rules"]
            chat_title = data["title"]

            await update.message.reply_text(
                f"📜 Rules\n\n{rules_text}"
            )

        else:
            await update.message.reply_text(
                "Rules not found."
            )

        return

    chat_type = update.effective_chat.type
    user = update.effective_user.first_name

    # GROUP START
    if chat_type in ["group", "supergroup"]:

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "Click me for help",
                    url=f"https://t.me/{context.bot.username}?start=help"
                )
            ]
        ])

        text = (
            f"Hello {user}, I'm your very own group manager!\n\n"
            "Click the help section button to learn how to use me "
            "to maximise your group's full potential."
        )

        await update.message.reply_text(text, reply_markup=keyboard)
        return

    # PRIVATE START
    await update.message.reply_text(
        main_text(),
        reply_markup=main_keyboard()
    )

# BACK BUTTON
async def help_back(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        main_text(),
        reply_markup=main_keyboard()
    )


# HELP MENU
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data
    text = None


    if data == "help_admin":

        text = """
👑 Admin Rank Commands

/grant - Assign a bot admin rank to a user.
Usage: reply to user with:
/grant <rank> <title>

/revoke - Remove a bot admin rank from a user.
Usage: reply to admin with:
/revoke

/admins - Show all bot admins with their ranks.

Rank hierarchy:
Owner > Dev > Sudo > Support
"""


    elif data == "help_mod":

            text = """
🛡 Moderation Commands

/ban - Ban a user from the current group.

/unban - Unban a user from the current group.

/promote - Promote a user to group admin.
Usage:
Reply to user:
/promote <admin title>

Or:
/promote <username> <admin title>

/demote - Remove a user's admin rights.
Usage:
Reply to admin:
/demote

Or:
/demote <username>

/lock - Lock the chat so only admins can send messages.

/unlock - Unlock the chat so everyone can talk.

/purge - Delete multiple messages quickly.
Usage: reply to a message then run /purge
"""


    elif data == "help_afk":

        text = """
💤 AFK System

/afk <reason> - Set yourself AFK.

If someone replies to you or mentions you,
the bot will notify them that you're away.

Sending any message will remove your AFK status automatically.
"""


    elif data == "help_hakai":

        text = """
☠ Hakai System

/hakai - Global ban a user from all groups where the bot has ban permission.
Only Owner and Dev rank admins can use this.

/unhakai - Remove global ban and unban the user from all groups where the bot has permission.
Only Owner and Dev rank admins can use this.
"""


    elif data == "help_notes":

        text = """
📒 Notes System

/save <name> <text> - Save a note.

/get <name> - Retrieve a saved note.

/notes - List all saved notes.

/clear <name> - Delete a saved note.

Quick trigger:
Use #notename to send a saved note instantly.
"""


    elif data == "help_warn":

        text = """
⚠ Warn System

/warn - Warn a user.
After 3 warns the user will be automatically banned.

/dwarn - Warn a user and delete their message.

/unwarn - Remove one warn.

/resetwarn - Reset all warns for a user.

/warns - Check warn count for a user.
"""


    elif data == "help_general":

        text = """
⚙ General Commands

/ping - Check if the bot is alive.

/everyone <message> - Mention everyone recorded in the group.
(Admin only)

/reportbug <bug> - Report a bug directly to the bot owner.
"""


    if text is None:
        return


    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅ Back", callback_data="help_back")]
    ])

    await query.edit_message_text(
        text,
        reply_markup=keyboard
    )



# REGISTER HANDLERS
def register_start(app):

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # BACK must be registered before help_
    app.add_handler(CallbackQueryHandler(help_back, pattern="^help_back$"))
    app.add_handler(CallbackQueryHandler(help_menu, pattern="^help_"))