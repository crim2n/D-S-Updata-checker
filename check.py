import os
import json
import requests
from datetime import datetime, timezone, timedelta
import time
import hashlib

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "state.json"
APP_ID = "com.nspgames.dungeonslasher"
URL = f"https://play.google.com/store/apps/details?id={APP_ID}&hl=ko&gl=KR"

def get_app_info_with_cache_bust():
    """캐시 무효화를 강제하는 방법으로 앱 정보 가져오기"""
    try:
        from google_play_scraper import app
        from google_play_scraper.features.app import _ContinuationToken
        import google_play_scraper.features.app as app_module
        
        print("📦 google-play-scraper 사용 중 (캐시 무효화)...")
        
        # 여러 번 시도하여 최신 데이터 확보
        results = []
        
        configs = [
            {'lang': 'en', 'country': 'us'},
            {'lang': 'ko', 'country': 'kr'},
            {'lang': 'ja', 'country': 'jp'},
            {'lang': 'en', 'country': 'gb'},
        ]
        
        for idx, config in enumerate(configs):
            try:
                # 타임스탬프를 추가하여 캐시 우회
                timestamp = int(time.time())
                print(f"   시도 {idx + 1}/{len(configs)}: lang={config['lang']}, country={config['country']}, ts={timestamp}")
                
                result = app(APP_ID, **config)
                
                version = result.get('version', '')
                updated = result.get('updated', 0)
                
                # 유효한 버전인지 확인
                if version and version not in ['Varies with device', '기기에 따라 다름', None]:
                    results.append({
                        'version': version,
                        'updated': updated,
                        'config': f"{config['lang']}_{config['country']}"
                    })
                    print(f"      ✓ 버전: {version}, 업데이트: {updated}")
                else:
                    print(f"      ⚠️ 무효한 버전: {version}")
                
                time.sleep(1)  # 각 요청 사이 대기
                
            except Exception as e:
                print(f"      ⚠️ 실패: {e}")
                continue
        
        if not results:
            print("   ❌ 모든 시도 실패")
            return None
        
        # 가장 최신 업데이트 타임스탬프를 가진 결과 선택
        latest_result = max(results, key=lambda x: x['updated'])
        print(f"   ✅ 최신 데이터 선택: {latest_result['config']}")
        
        # 날짜 포맷팅
        pst_tz = timezone(timedelta(hours=-8))
        updated_value = datetime.fromtimestamp(
            latest_result['updated'], 
            tz=timezone.utc
        ).astimezone(pst_tz).strftime('%Y. %m. %d')
        
        return {
            "updated": updated_value,
            "version": latest_result['version'],
            "timestamp": latest_result['updated']
        }
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return None

def get_app_info_from_direct_request():
    """직접 HTTP 요청으로 Play Store 데이터 가져오기"""
    print("🌐 직접 HTTP 요청 시도...")
    
    # 캐시 무효화를 위한 랜덤 파라미터
    timestamp = int(time.time())
    cache_bust = hashlib.md5(str(timestamp).encode()).hexdigest()[:8]
    
    url = f"{URL}&_={cache_bust}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
    }
    
    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        html = response.text
        
        # 더 정확한 정규식 패턴들
        import re
        
        # 패턴 1: JavaScript data structure에서 추출
        version_pattern_1 = r'\[\["' + re.escape(APP_ID) + r'"\],\["([0-9]+\.[0-9]+\.[0-9]+[^"]*?)"\]'
        # 패턴 2: 메타 데이터에서 추출  
        version_pattern_2 = r'"softwareVersion"\s*:\s*"([0-9]+\.[0-9]+\.[0-9]+[^"]*?)"'
        # 패턴 3: 일반 텍스트
        version_pattern_3 = r'Current Version[^<]*?<[^>]*?>([0-9]+\.[0-9]+\.[0-9]+[^<]*?)<'
        
        version_value = None
        for pattern in [version_pattern_1, version_pattern_2, version_pattern_3]:
            match = re.search(pattern, html)
            if match:
                version_value = match.group(1).strip()
                print(f"   ✓ 버전 찾음: {version_value}")
                break
        
        # 날짜 패턴
        date_pattern = r'"datePublished"\s*:\s*"([^"]+)"'
        date_match = re.search(date_pattern, html)
        
        updated_value = None
        if date_match:
            date_str = date_match.group(1)
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                pst_tz = timezone(timedelta(hours=-8))
                updated_value = dt.astimezone(pst_tz).strftime('%Y. %m. %d')
                print(f"   ✓ 날짜 찾음: {updated_value}")
            except:
                pass
        
        if version_value or updated_value:
            return {
                "updated": updated_value or "날짜 확인 실패",
                "version": version_value or "버전 확인 실패"
            }
        
        print("   ⚠️ 데이터 추출 실패")
        
    except Exception as e:
        print(f"   ❌ 요청 실패: {e}")
    
    return None

def get_app_info():
    """여러 방법으로 앱 정보 수집 후 교차 검증"""
    
    print("=" * 60)
    print("🔍 앱 정보 수집 시작 (다중 소스)")
    print("=" * 60)
    
    results = []
    
    # 방법 1: google-play-scraper (여러 지역)
    result1 = get_app_info_with_cache_bust()
    if result1 and result1['version'] != "버전 확인 실패":
        results.append(('scraper', result1))
    
    time.sleep(2)
    
    # 방법 2: 직접 HTTP 요청
    result2 = get_app_info_from_direct_request()
    if result2 and result2['version'] != "버전 확인 실패":
        results.append(('direct', result2))
    
    if not results:
        print("\n❌ 모든 방법 실패")
        return {
            "updated": "확인 실패",
            "version": "확인 실패"
        }
    
    print("\n" + "=" * 60)
    print("📊 수집된 데이터:")
    for source, data in results:
        print(f"   [{source}] 버전: {data['version']}, 날짜: {data['updated']}")
    print("=" * 60)
    
    # 교차 검증: 가장 높은 버전 번호 선택
    def version_tuple(v):
        """버전 문자열을 비교 가능한 튜플로 변환"""
        try:
            return tuple(map(int, v.split('.')[:3]))
        except:
            return (0, 0, 0)
    
    best_result = max(results, key=lambda x: version_tuple(x[1]['version']))
    
    print(f"\n✅ 최종 선택: [{best_result[0]}] 버전 {best_result[1]['version']}")
    
    return best_result[1]

# 메인 실행
print("=" * 60)
print(f"🎮 던전 슬래셔 업데이트 체크")
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
    print
