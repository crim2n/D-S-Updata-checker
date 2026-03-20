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

def get_app_info_from_api():
    """Google Play Store Internal API 사용"""
    
    api_url = "https://play.google.com/_ah/api/phoneskyservice/v1/getAppDetails"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'ko-KR,ko;q=0.9',
    }
    
    params = {
        'doc': APP_ID,
        'hl': 'ko',
        'gl': 'KR'
    }
    
    try:
        print("🌐 Google Play API 요청 중...")
        response = requests.get(api_url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            version_value = data.get('versionString', None)
            updated_timestamp = data.get('uploadDate', None)
            
            if version_value:
                print(f"   ✓ 버전 찾음 (API): {version_value}")
            
            if updated_timestamp:
                pst_tz = timezone(timedelta(hours=-8))
                updated_value = datetime.fromtimestamp(
                    updated_timestamp / 1000,  # 밀리초를 초로 변환
                    tz=timezone.utc
                ).astimezone(pst_tz).strftime('%Y. %m. %d')
                print(f"   ✓ 날짜 찾음 (API): {updated_value}")
                
                return {
                    "updated": updated_value,
                    "version": version_value or "버전 확인 실패"
                }
    except Exception as e:
        print(f"   ⚠️ API 요청 실패: {e}")
    
    return None

def get_app_info_from_scraper():
    """google-play-scraper 라이브러리 사용 (개선)"""
    try:
        from google_play_scraper import app
        print("📦 google-play-scraper 사용 중...")
        
        # 여러 언어/지역 조합 시도
        combinations = [
            {'lang': 'ko', 'country': 'kr'},
            {'lang': 'en', 'country': 'us'},
            {'lang': 'en', 'country': 'kr'},
        ]
        
        for idx, combo in enumerate(combinations):
            try:
                print(f"   시도 {idx + 1}: lang={combo['lang']}, country={combo['country']}")
                result = app(APP_ID, **combo)
                
                version_value = result.get('version')
                updated_timestamp = result.get('updated')
                
                if version_value and version_value != "Varies with device":
                    print(f"   ✓ 버전 찾음: {version_value}")
                    
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
                else:
                    print(f"   ⚠️ 유효한 버전 정보 없음: {version_value}")
                    
            except Exception as e:
                print(f"   ⚠️ 실패: {e}")
                continue
        
        print("   ❌ 모든 조합 실패")
        
    except Exception as e:
        print(f"❌ google-play-scraper 오류: {e}")
    
    return None

def get_app_info_from_web():
    """웹 스크래핑 방식 (최후 수단)"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    try:
        print("🌐 웹 스크래핑 시도 중...")
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text
        
        # 초기 데이터 스크립트 찾기
        script_match = re.search(r'AF_initDataCallback\((.*?)\);</script>', html, re.DOTALL)
        
        if script_match:
            script_content = script_match.group(1)
            
            # 버전 정보 (여러 패턴)
            version_patterns = [
                r'\["([0-9]+\.[0-9]+\.[0-9]+[^"]*?)"\].*?htlgb',  # 버전 패턴 1
                r'현재\s*버전.*?>([\d\.]+)<',  # 한글 페이지
                r'"versionName"\s*:\s*"([^"]+)"',  # JSON 형식
            ]
            
            version_value = None
            for pattern in version_patterns:
                match = re.search(pattern, html)
                if match:
                    version_value = match.group(1).strip()
                    if version_value and not any(x in version_value.lower() for x in ['varies', 'device', '기기']):
                        print(f"   ✓ 버전 찾음: {version_value}")
                        break
            
            # 날짜 정보
            date_patterns = [
                r'"datePublished"\s*:\s*"([^"]+)"',
                r'업데이트\s*날짜.*?>([\d]+\.\s*[\d]+\.\s*[\d]+)',
            ]
            
            updated_value = None
            for pattern in date_patterns:
                match = re.search(pattern, html)
                if match:
                    date_str = match.group(1).strip()
                    
                    # ISO 형식 변환
                    if 'T' in date_str or '-' in date_str:
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
            
            if version_value or updated_value:
                return {
                    "updated": updated_value or "날짜 확인 실패",
                    "version": version_value or "버전 확인 실패"
                }
        
        print("   ⚠️ 데이터를 찾을 수 없음")
        
    except Exception as e:
        print(f"   ❌ 웹 스크래핑 실패: {e}")
    
    return None

def get_app_info(max_retries=2):
    """여러 방법을 순차적으로 시도"""
    
    methods = [
        ("google-play-scraper", get_app_info_from_scraper),
        ("Web Scraping", get_app_info_from_web),
    ]
    
    for method_name, method_func in methods:
        for attempt in range(max_retries):
            try:
                result = method_func()
                
                if result and result['version'] != "버전 확인 실패":
                    print(f"✅ {method_name} 성공!")
                    return result
                
                if attempt < max_retries - 1:
                    print(f"   재시도 중... ({attempt + 2}/{max_retries})")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"   오류: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        print(f"   {method_name} 실패, 다음 방법 시도...\n")
    
    print("❌ 모든 방법 실패")
    return {
        "updated": "확인 실패",
        "version": "확인 실패"
    }

# 메인 실행
print("=" * 60)
print(f"🎮 던전 슬래셔 업데이트 체크 시작")
print(f"⏰ 실행 시간: {datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S KST')}")
print("=" * 60)

# 앱 정보 가져오기
current_data = get_app_info()

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

# "확인 실패"가 아닌 경우에만 비교
if current_data['version'] != "확인 실패" and current_data['updated'] != "확인 실패":
    version_changed = old_data.get("version") != current_data["version"]
    date_changed = old_data.get("updated") != current_data["updated"]
    
    if version_changed or date_changed:
        print("\n" + "=" * 60)
        print("🔔 변경 감지!")
        
        if version_changed:
            print(f"   📦 버전: {old_data.get('version', 'N/A')} → {current_data['version']}")
        if date_changed:
            print(f"   📅 날짜: {old_data.get('updated', 'N/A')} → {current_data['updated']}")
        
        print("=" * 60)
        
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
else:
    print("\n⚠️ 데이터 확인 실패로 인해 변경 감지 스킵")

print("=" * 60)
