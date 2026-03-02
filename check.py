import os
import json
import requests
from google_play_scraper import app
from datetime import datetime

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "state.json"
APP_ID = "com.nspgames.dungeonslasher"
URL = f"https://play.google.com/store/apps/details?id={APP_ID}&hl=ko&gl=KR"

try:
    # google-play-scraper를 이용해 앱 데이터 가져오기
    result = app(
        APP_ID,
        lang='ko', 
        country='kr'
    )
    
    # 버전 정보 가져오기
    version_value = result.get('version', '버전 확인 실패')
    
    # 업데이트 날짜 가져오기 (타임스탬프를 보기 좋은 날짜 형식으로 변환)
    updated_timestamp = result.get('updated')
    if updated_timestamp:
        updated_value = datetime.fromtimestamp(updated_timestamp).strftime('%Y. %m. %d')
    else:
        updated_value = "날짜 확인 실패"

except Exception as e:
    print(f"데이터 스크래핑 실패: {e}")
    exit(1)

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

# 버전이나 날짜가 이전과 다를 경우에만 알림 전송
if old_data.get("version") != current_data["version"] or old_data.get("updated") != current_data["updated"]:
    msg = (
        "🔥 던전 슬래셔 업데이트 감지!\n"
        f"📦 버전: {version_value}\n"
        f"📅 업데이트 날짜: {updated_value}\n"
        f"{URL}"
    )
    requests.post(WEBHOOK, json={"content": msg})

    # 새로운 상태 저장
    with open(STATE_FILE, "w") as f:
        json.dump(current_data, f)
    print("업데이트 알림 전송 완료 및 상태 저장됨")
else:
    print("변경 없음")
