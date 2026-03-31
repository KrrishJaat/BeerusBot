from telegram.ext import ApplicationBuilder
from telegram import Update

from config import BOT_TOKEN

from modules.build import register_build
from modules.moderation import register_moderation
from modules.warns import register_warns
from modules.notes import register_notes
from modules.afk import register_afk
from modules.currency import register_currency
from modules.report import register_report
from modules.hakai import register_hakai
from modules.reply import register_reply
from modules.everyone import register_everyone
from modules.groups import register_groups
from modules.start import register_start
from modules.info import register_info
from modules.user_cache import register_user_cache
from modules.firmware import register_firmware
from modules.getrom import register_getrom
from modules.translate import register_translate
from modules.greetings import register_greetings
from modules.mute import register_mute
from modules.adminlogs import register_adminlogs

app = ApplicationBuilder().token(BOT_TOKEN).build()


# REGISTER MODULES
register_build(app)
register_moderation(app)
register_warns(app)
register_notes(app)
register_afk(app)
register_currency(app)
register_report(app)
register_hakai(app)
register_groups(app)
register_reply(app)
register_everyone(app)
register_start(app)
register_info(app)
register_user_cache(app)
register_firmware(app)
register_getrom(app)
register_translate(app)
register_greetings(app)
register_mute(app)
register_adminlogs(app)

async def error_handler(update, context):
    print(context.error)

app.add_error_handler(error_handler)

print("Beerus Is Ready For Destruction...")

app.run_polling(allowed_updates=Update.ALL_TYPES)
