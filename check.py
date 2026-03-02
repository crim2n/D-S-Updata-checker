import requests
from bs4 import BeautifulSoup
import os
import json
import re

URL = "https://play.google.com/store/apps/details?id=com.nspgames.dungeonslasher&hl=ko&gl=KR"
WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "state.json"

headers = {
    "User-Agent": "Mozilla/5.0"
}

res = requests.get(URL, headers=headers)
soup = BeautifulSoup(res.text, "html.parser")

# __NEXT_DATA__ JSON 가져오기
next_data = soup.find("script", id="__NEXT_DATA__")
data = json.loads(next_data.string)

# JSON 내부에서 버전/업데이트 정보 찾기
page_props = data["props"]["pageProps"]

app_data = page_props["appDetails"]

version_value = app_data.get("version", "버전 확인 실패")
updated_value = app_data.get("updated", "날짜 확인 실패")

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
