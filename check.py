import os
import json
import requests
from datetime import datetime, timezone, timedelta
import time

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "state.json"
APP_ID = "com.nspgames.dungeonslasher"
URL = f"https://play.google.com/store/apps/details?id={APP_ID}&hl=ko&gl=KR"

def get_app_info_with_retry(max_retries=3):
    """재시도 로직을 포함한 앱 정보 가져오기"""
    from google_play_scraper import app
    
    for attempt in range(max_retries):
        try:
            # 캐시 방지를 위해 매번 새로운 요청
            result = app(
                APP_ID, 
                lang='ko', 
                country='kr'
            )
            
            version_value = result.get('version', None)
            updated_timestamp = result.get('updated', None)
            
            # 버전 정보가 없으면 재시도
            if not version_value:
                print(f"⚠️ 버전 정보 없음 (시도 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 2초 대기 후 재시도
                    continue
                else:
                    version_value = "버전 확인 실패"
            
            # 날짜 포맷팅
            if updated_timestamp:
                pst_tz = timezone(timedelta(hours=-8))
                updated_value = datetime.fromtimestamp(
                    updated_timestamp, 
                    tz=timezone.utc
                ).astimezone(pst_tz).strftime('%Y. %m. %d')
            else:
                updated_value = "날짜 확인 실패"
            
            # 디버깅 정보 출력
            print(f"📱 현재 앱 정보:")
            print(f"   버전: {version_value}")
            print(f"   업데이트: {updated_value}")
            print(f"   원본 타임스탬프: {updated_timestamp}")
            
            return {
                "updated": updated_value,
                "version": version_value,
                "timestamp": updated_timestamp
            }
            
        except Exception as e:
            print(f"❌ 데이터 스크래핑 실패 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                exit(1)

# 앱 정보 가져오기
current_data = get_app_info_with_retry()

# 이전 상태 로드
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding='utf-8') as f:
        old_data = json.load(f)
    print(f"📂 이전 상태:")
    print(f"   버전: {old_data.get('version', 'N/A')}")
    print(f"   업데이트: {old_data.get('updated', 'N/A')}")
else:
    old_data = {}
    print("📂 이전 상태 파일 없음 (첫 실행)")

# 변경 감지 (버전 OR 날짜 변경)
version_changed = old_data.get("version") != current_data["version"]
date_changed = old_data.get("updated") != current_data["updated"]

if version_changed or date_changed:
    # 변경 내용 상세 출력
    changes = []
    if version_changed:
        changes.append(f"버전: {old_data.get('version', 'N/A')} → {current_data['version']}")
    if date_changed:
        changes.append(f"날짜: {old_data.get('updated', 'N/A')} → {current_data['updated']}")
    
    print(f"🔔 변경 감지!")
    for change in changes:
        print(f"   {change}")
    
    # Discord 알림 전송
    msg = (
        "🔥 던전 슬래셔 업데이트 감지!\n"
        f"📦 버전: {current_data['version']}\n"
        f"📅 업데이트 날짜: {current_data['updated']}\n"
        f"{URL}"
    )
    
    try:
        response = requests.post(WEBHOOK, json={"content": msg}, timeout=10)
        response.raise_for_status()
        print("✅ Discord 알림 전송 완료")
    except Exception as e:
        print(f"⚠️ Discord 알림 전송 실패: {e}")
    
    # 상태 저장
    with open(STATE_FILE, "w", encoding='utf-8') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)
    print("💾 상태 저장 완료")
    
else:
    print("✨ 변경 없음")
