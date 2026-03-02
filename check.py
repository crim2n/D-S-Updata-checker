import requests
from bs4 import BeautifulSoup
import os
import json

URL = "https://play.google.com/store/apps/details?id=com.nspgames.dungeonslasher&hl=ko&gl=KR"
WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "state.json"

headers = {
    "User-Agent": "Mozilla/5.0"
}

res = requests.get(URL, headers=headers)
soup = BeautifulSoup(res.text, "html.parser")

# 업데이트 날짜 찾기
updated_text = soup.find(string=lambda x: x and "업데이트" in x or "Updated" in x)
updated_value = updated_text.find_next().text.strip()

# 현재 버전 찾기
version_text = soup.find(string=lambda x: x and "현재 버전" in x or "Current Version" in x)
version_value = version_text.find_next().text.strip()

current_data = {
    "updated": updated_value,
    "version": version_value
}

# 이전 상태 불러오기
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        old_data = json.load(f)
else:
    old_data = {}

if old_data != current_data:
    msg = (
        "🔥 던전 슬래셔 업데이트 감지!\n"
        f"📦 버전: {version_value}\n"
        f"📅 업데이트 날짜: {updated_value}\n"
        f"{URL}"
    )
    requests.post(WEBHOOK, json={"content": msg})

    with open(STATE_FILE, "w") as f:
        json.dump(current_data, f)
else:
    print("변경 없음")
