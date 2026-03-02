from google_play_scraper import app
import os
import json
import requests

APP_ID = "com.nspgames.dungeonslasher"
WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "state.json"

result = app(APP_ID, lang="ko", country="kr")

version_value = result["version"]
updated_value = result["updated"]

current_data = {
    "updated": updated_value,
    "version": version_value
}

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        old_data = json.load(f)
else:
    old_data = {}

if old_data != current_data:
    msg = (
        "🔥 던전 슬래셔 업데이트 감지!\n"
        f"📦 버전: {version_value}\n"
        f"📅 업데이트 날짜: {updated_value}"
    )
    requests.post(WEBHOOK, json={"content": msg})

    with open(STATE_FILE, "w") as f:
        json.dump(current_data, f)
