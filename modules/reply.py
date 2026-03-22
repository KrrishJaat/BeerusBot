import random

from telegram import Update
from telegram.ext import MessageHandler, ContextTypes, filters

from config import OWNER_ID


async def bot_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if not update.message.reply_to_message:
        return

    if update.message.reply_to_message.from_user.id != context.bot.id:
        return

    # FIX: handle messages without text
    if not update.message.text:
        return

    text = update.message.text.lower()

    bad_words = ["fuck", "fuck you", "fuck u", "ass", "shit", "nigga"]

    if any(word in text for word in bad_words):

        user_id = update.effective_user.id

        if user_id == OWNER_ID:
            await update.message.reply_text("Sorry boss, my bad.")
            return

        replies = [
            "Watch your language.",
            "Try again without the attitude.",
            "Calm down keyboard warrior.",
            "Relax bro, it's just a bot.",
            "Someone woke up angry today.",
            "Touch grass maybe?",
            "That wasn't very nice.",
            "Be respectful or I'll ignore you.",
            "Did that make you feel better?",
            "Take a deep breath and try again.",
            "You're arguing with a bot. Think about that.",
            "I'm just code and I'm already disappointed.",
            "Internet tough guy detected.",
            "Error: manners not found.",
            "That energy could be used for something productive.",
            "You good bro?",
            "I'm not offended, just confused.",
            "Maybe step away from the keyboard for a bit.",
            "That wasn't very constructive.",
            "You seem upset. Everything okay?",
            "I process ROM builds, not tantrums.",
            "Your message has been evaluated... and rejected.",
            "Congratulations, you insulted a bot.",
            "If anger burned calories you'd be shredded.",
            "Try again, but with manners this time.",
            "404: Respect not found.",
            "That wasn't in the user manual.",
            "I think your keyboard is stuck on angry mode.",
            "Maybe drink some water and try again.",
            "Are we done here?",
            "I'm running on Python, not patience.",
            "I came here to build ROMs, not hear rants.",
            "Your input has been ignored successfully.",
            "You're yelling at a machine. Just saying.",
            "System recommendation: calm down.",
            "Interesting strategy, but no.",
            "I'll pretend I didn't hear that.",
            "Not my fault your build failed.",
            "Try debugging your attitude first.",
            "This conversation is not compiling.",
            "Error: attitude overflow.",
            "Your message has low signal, high noise.",
            "I detect unnecessary hostility.",
            "That wasn't very ROM-compatible behavior.",
            "Let's keep it civil, shall we?",
            "Maybe reboot your mood.",
            "That comment needs a patch.",
            "Consider upgrading your manners.",
            "I've processed worse, but this is close.",
            "Negative vibes detected.",
            "You sound like a broken build log.",
            "Let's keep the chat readable.",
            "That comment failed validation.",
            "Your tone requires an update.",
            "I'm logging this as unnecessary drama.",
            "Calm down before I start compiling sarcasm.",
            "This bot prefers peaceful commits.",
            "Let's downgrade the hostility.",
            "That message needs a rollback.",
            "You're talking big for someone arguing with a bot.",
            "System notice: chill mode recommended.",
            "Message rejected due to excessive salt.",
            "I only accept clean input.",
            "This chat isn't a rage server.",
            "That tone isn't supported.",
            "Let's keep the repo clean.",
            "That energy isn't productive.",
            "User mood: unstable.",
            "Please update your attitude module.",
            "End of line."
        ]

        await update.message.reply_text(random.choice(replies))


def register_reply(app):

    app.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), bot_protection),
        group=4
    )