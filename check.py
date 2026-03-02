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

# 페이지 전체 텍스트에서 버전 패턴 찾기 (숫자.숫자 형태)
page_text = soup.get_text()

version_match = re.search(r"\d+\.\d+(\.\d+)?", page_text)
version_value = version_match.group() if version_match else "버전 확인 실패"

# 업데이트 날짜 찾기
updated_match = re.search(r"\d{4}\.\s?\d{1,2}\.\s?\d{1,2}", page_text)
updated_value = updated_match.group() if updated_match else "날짜 확인 실패"

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
