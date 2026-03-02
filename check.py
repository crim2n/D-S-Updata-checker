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

# "Updated on" 또는 "업데이트 날짜" 부분 찾기
updated_section = soup.find(string=lambda x: x and "업데이트" in x or "Updated" in x)
updated_value = updated_section.find_next().text.strip()

# 이전 상태 불러오기
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        old_data = json.load(f)
else:
    old_data = {"updated": ""}

if old_data["updated"] != updated_value:
    msg = f"🔥 던전 슬래셔 업데이트 감지!\n📅 업데이트 날짜: {updated_value}\n{URL}"
    requests.post(WEBHOOK, json={"content": msg})
    with open(STATE_FILE, "w") as f:
        json.dump({"updated": updated_value}, f)
else:
    print("변경 없음")
