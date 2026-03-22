import requests
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes

from config import OWNER_ID, GITHUB_TOKEN, REPO_OWNER, REPO_NAME, WORKFLOW_FILE, allowed_devices

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


def get_recent_runs():

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs"

    r = requests.get(url, headers=headers)

    runs = r.json()["workflow_runs"]

    return runs[:20]

def cancel_build(device):

    runs = get_recent_runs()

    for run in runs:

        title = run["display_title"]

        if ">" not in title:
            continue

        run_device = title.split(">")[-1].strip()

        if run_device != device:
            continue

        if run["status"] not in ["queued", "in_progress"]:
            continue

        run_id = run["id"]

        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}/cancel"

        r = requests.post(url, headers=headers)

        if r.status_code == 202:
            return True

    return False

def trigger_workflow(device):

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/dispatches"

    data = {
        "ref": "main",
        "inputs": {
            "device": device,
            "upload_cloud": True
        }
    }

    r = requests.post(url, headers=headers, json=data)

    return r.status_code == 204


# BUILD COMMAND
async def buildrom(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Bitch You're not Worthy.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /buildrom <device>")
        return

    device = context.args[0]

    if device not in allowed_devices:
        await update.message.reply_text("device not eligible")
        return

    ok = trigger_workflow(device)

    if ok:

        message = (
            f"🚀 *ReCoreUI Build Triggered*\n\n"
            f"📱 *Device:* `{device}`\n"
            f"⚙️ *Status:* Starting build\n"
            f"☁️ *Upload:* GoFile\n\n"
            f"⏳ Waiting for GitHub runner..."
        )

        await update.message.reply_text(message, parse_mode="Markdown")

    else:
        await update.message.reply_text("Failed to trigger workflow")


# BUILD STATUS
async def buildstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        runs = get_recent_runs()

        device_status = {}
        buttons = []

        for run in runs:

            title = run["display_title"]

            if ">" not in title:
                continue

            device = title.split(">")[-1].strip()

            if device in device_status:
                continue

            status = run["status"]
            conclusion = run["conclusion"]
            url = run["html_url"]

            if status == "queued":
                icon = "🟡"
                status_text = "Queued"

            elif status == "in_progress":
                icon = "⚙️"
                status_text = "Running"

            elif status == "completed":

                if conclusion == "success":
                    icon = "🟢"
                    status_text = "Completed"

                elif conclusion == "failure":
                    icon = "🔴"
                    status_text = "Failed"

                else:
                    icon = "⚪"
                    status_text = conclusion

            else:
                icon = "⚪"
                status_text = status

            device_status[device] = (icon, status_text, url)

        message = "📦 *ReCoreUI Build Status*\n\n"

        for device, (icon, status, url) in device_status.items():

            message += f"{icon} `{device}` → {status}\n"

            buttons.append([InlineKeyboardButton(device, url=url)])

        keyboard = InlineKeyboardMarkup(buttons)

        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:

        print(e)

        await update.message.reply_text("Unable to fetch build status.")

async def buildstop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Bitch You're not Worthy.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /buildstop <device>")
        return

    device = context.args[0]

    if device not in allowed_devices:
        await update.message.reply_text("Invalid device.")
        return

    cancelled = cancel_build(device)

    if cancelled:
        await update.message.reply_text(
            f"🛑 Build cancelled for `{device}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"No running build found for `{device}`"
        )

def register_build(app):

    app.add_handler(CommandHandler("buildrom", buildrom), group=0)
    app.add_handler(CommandHandler("buildstatus", buildstatus), group=0)
    app.add_handler(CommandHandler("buildstop", buildstop), group=0)
