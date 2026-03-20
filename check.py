import os
import json
import requests
from datetime import datetime, timezone, timedelta
import re
import time

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "state.json"
APP_ID = "com.nspgames.dungeonslasher"
URL = f"https://play.google.com/store/apps/details?id={APP_ID}&hl=ko&gl=KR"

def get_app_info_from_web(max_retries=3):
    """플레이스토어 웹페이지에서 직접 정보 가져오기"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    for attempt in range(max_retries):
        try:
            print(f"🌐 웹페이지 요청 중... (시도 {attempt + 1}/{max_retries})")
            
            response = requests.get(URL, headers=headers, timeout=15)
            response.raise_for_status()
            html = response.text
            
            # 버전 정보 추출 (여러 패턴 시도)
            version_patterns = [
                r'"versionName":"([^"]+)"',
                r'현재 버전</div>.*?<span.*?>([^<]+)</span>',
                r'Current Version</div>.*?<span.*?>([^<]+)</span>',
                r'softwareVersion">\s*([^<]+)\s*<',
            ]
            
            version_value = None
            for pattern in version_patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    version_value = match.group(1).strip()
                    print(f"   ✓ 버전 찾음 (패턴 {version_patterns.index(pattern) + 1}): {version_value}")
                    break
            
            if not version_value:
                print("   ⚠️ 버전 정보를 찾을 수 없음")
                version_value = "버전 확인 실패"
            
            # 업데이트 날짜 추출
            date_patterns = [
                r'"datePublished":"([^"]+)"',
                r'업데이트 날짜</div>.*?<span.*?>([^<]+)</span>',
                r'Updated on</div>.*?<span.*?>([^<]+)</span>',
            ]
            
            updated_value = None
            for pattern in date_patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    date_str = match.group(1).strip()
                    
                    # ISO 형식이면 변환
                    if 'T' in date_str:
                        try:
                            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            pst_tz = timezone(timedelta(hours=-8))
                            updated_value = dt.astimezone(pst_tz).strftime('%Y. %m. %d')
                        except:
                            updated_value = date_str
                    else:
                        updated_value = date_str
                    
                    print(f"   ✓ 날짜 찾음: {updated_value}")
                    break
            
            if not updated_value:
                print("   ⚠️ 날짜 정보를 찾을 수 없음")
                updated_value = "날짜 확인 실패"
            
            return {
                "updated": updated_value,
                "version": version_value
            }
            
        except requests.RequestException as e:
            print(f"   ❌ 요청 실패: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
                continue
            else:
                print("   ⚠️ 최대 재시도 횟수 초과, google-play-scraper로 폴백")
                return get_app_info_fallback()
        except Exception as e:
            print(f"   ❌ 파싱 실패: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
                continue
            else:
                return get_app_info_fallback()

def get_app_info_fallback():
    """폴백: google-play-scraper 사용"""
    try:
        from google_play_scraper import app
        print("📦 google-play-scraper 사용 중...")
        
        result = app(APP_ID, lang='ko', country='kr')
        version_value = result.get('version', '버전 확인 실패')
        
        updated_timestamp = result.get('updated')
        if updated_timestamp:
            pst_tz = timezone(timedelta(hours=-8))
            updated_value = datetime.fromtimestamp(
                updated_timestamp, 
                tz=timezone.utc
            ).astimezone(pst_tz).strftime('%Y. %m. %d')
        else:
            updated_value = "날짜 확인 실패"
        
        return {
            "updated": updated_value,
            "version": version_value
        }
    except Exception as e:
        print(f"❌ 폴백도 실패: {e}")
        exit(1)

# 메인 실행
print("=" * 50)
print(f"🎮 던전 슬래셔 업데이트 체크 시작")
print(f"⏰ 실행 시간: {datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S KST')}")
print("=" * 50)

# 앱 정보 가져오기
current_data = get_app_info_from_web()

print(f"\n📱 현재 정보:")
print(f"   버전: {current_data['version']}")
print(f"   업데이트: {current_data['updated']}")

# 이전 상태 로드
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding='utf-8') as f:
        old_data = json.load(f)
    print(f"\n📂 이전 정보:")
    print(f"   버전: {old_data.get('version', 'N/A')}")
    print(f"   업데이트: {old_data.get('updated', 'N/A')}")
else:
    old_data = {}
    print("\n📂 이전 상태 파일 없음 (첫 실행)")

# 변경 감지
version_changed = old_data.get("version") != current_data["version"]
date_changed = old_data.get("updated") != current_data["updated"]

if version_changed or date_changed:
    print("\n" + "=" * 50)
    print("🔔 변경 감지!")
    
    if version_changed:
        print(f"   📦 버전: {old_data.get('version', 'N/A')} → {current_data['version']}")
    if date_changed:
        print(f"   📅 날짜: {old_data.get('updated', 'N/A')} → {current_data['updated']}")
    
    print("=" * 50)
    
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
    print("\n✨ 변경 없음")

print("=" * 50)
