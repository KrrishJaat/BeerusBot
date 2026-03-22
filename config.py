import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

REPO_OWNER = "KrrishJaat"
REPO_NAME = "ReCoreUI"
WORKFLOW_FILE = "build-rom.yml"

allowed_devices = ["m14x", "a14x", "f14x"]