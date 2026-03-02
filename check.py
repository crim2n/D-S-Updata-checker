import os
import json
import requests
from google_play_scraper import app
from datetime import datetime, timezone, timedelta

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "state.json"
APP_ID = "com.nspgames.dungeonslasher"
URL = f"https://play.google.com/store/apps/details?id={APP_ID}&hl=ko&gl=KR"

try:
    result = app(APP_ID, lang='ko', country='kr')
    version_value = result.get('version', '버전 확인 실패')
    
    updated_timestamp = result.get('updated')
    if updated_timestamp:
        # 구글 플레이스토어 웹과 동일하게 맞추기 위해 미국 태평양 표준시(PST, UTC-8) 적용
        pst_tz = timezone(timedelta(hours=-8))
        # 타임스탬프를 UTC로 인식한 뒤 PST로 변환하여 텍스트로 출력
        updated_value = datetime.fromtimestamp(updated_timestamp, tz=timezone.utc).astimezone(pst_tz).strftime('%Y. %m. %d')
    else:
        updated_value = "날짜 확인 실패"

except Exception as e:
    print(f"데이터 스크래핑 실패: {e}")
    exit(1)

current_data = {
    "updated": updated_value,
    "version": version_value
}

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

    with open(STATE_FILE, "w") as f:
        json.dump(current_data, f)
    print("업데이트 알림 전송 완료 및 상태 저장됨")
else:
    print("변경 없음")
