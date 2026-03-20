import os
import json
import requests
from datetime import datetime, timezone, timedelta
import time

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "state.json"
APP_ID = "com.nspgames.dungeonslasher"
URL = f"https://play.google.com/store/apps/details?id={APP_ID}&hl=ko&gl=KR"

def get_app_info():
    """google-play-scraper 사용 (간단 버전)"""
    try:
        from google_play_scraper import app
        
        print("📦 앱 정보 가져오는 중...")
        
        # 영어/미국 버전이 가장 빠르게 업데이트됨
        result = app(APP_ID, lang='en', country='us')
        
        version = result.get('version', '확인 실패')
        updated_timestamp = result.get('updated', 0)
        
        if updated_timestamp:
            pst_tz = timezone(timedelta(hours=-8))
            updated = datetime.fromtimestamp(
                updated_timestamp, 
                tz=timezone.utc
            ).astimezone(pst_tz).strftime('%Y. %m. %d')
        else:
            updated = "날짜 확인 실패"
        
        print(f"   버전: {version}")
        print(f"   날짜: {updated}")
        print(f"   타임스탬프: {updated_timestamp}")
        
        return {
            "version": version,
            "updated": updated,
            "timestamp": updated_timestamp
        }
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return None

# 메인 실행
print("=" * 60)
print(f"🎮 던전 슬래셔 업데이트 체크")
kst = timezone(timedelta(hours=9))
now = datetime.now(kst)
print(f"⏰ 실행: {now.strftime('%Y-%m-%d %H:%M:%S KST')}")
print("=" * 60)

# 정보 가져오기
current_data = get_app_info()

if not current_data:
    print("❌ 데이터 수집 실패")
    exit(1)

print(f"\n📱 현재:")
print(f"   버전: {current_data['version']}")
print(f"   날짜: {current_data['updated']}")

# 이전 상태 로드
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding='utf-8') as f:
        old_data = json.load(f)
    print(f"\n📂 이전:")
    print(f"   버전: {old_data.get('version', 'N/A')}")
    print(f"   날짜: {old_data.get('updated', 'N/A')}")
else:
    old_data = {}
    print("\n📂 첫 실행")

# 변경 확인
version_changed = old_data.get("version") != current_data["version"]
date_changed = old_data.get("updated") != current_data["updated"]

if version_changed or date_changed:
    print("\n" + "=" * 60)
    print("🔔 업데이트 감지!")
    
    if version_changed:
        print(f"📦 {old_data.get('version', '없음')} → {current_data['version']}")
    if date_changed:
        print(f"📅 {old_data.get('updated', '없음')} → {current_data['updated']}")
    
    print("=" * 60)
    
    # Discord 알림
    msg = (
        "🔥 던전 슬래셔 업데이트 감지!\n"
        f"📦 버전: {current_data['version']}\n"
        f"📅 업데이트 날짜: {current_data['updated']}\n"
        f"{URL}"
    )
    
    try:
        response = requests.post(WEBHOOK, json={"content": msg}, timeout=10)
        response.raise_for_status()
        print("✅ 알림 전송 완료")
    except Exception as e:
        print(f"⚠️ 알림 실패: {e}")
    
    # 저장
    with open(STATE_FILE, "w", encoding='utf-8') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)
    print("💾 저장 완료")
    
else:
    print("\n✨ 변경 없음")

print("=" * 60)
