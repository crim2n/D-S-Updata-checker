import os
import json
import requests
from datetime import datetime, timezone, timedelta
import re
import time
import subprocess
import sys

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "state.json"
APP_ID = "com.nspgames.dungeonslasher"
URL = f"https://play.google.com/store/apps/details?id={APP_ID}&hl=ko&gl=KR"

def get_version_from_web_multiple_attempts():
    """여러 번 시도하여 최신 버전 확보"""
    
    print("🌐 웹에서 직접 버전 정보 가져오기...")
    
    # 다양한 User-Agent와 헤더 조합
    attempts_configs = [
        {
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
            },
            'url': f"https://play.google.com/store/apps/details?id={APP_ID}&hl=en&gl=US"
        },
        {
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept-Language': 'ko-KR,ko;q=0.9',
                'Cache-Control': 'no-cache',
            },
            'url': f"https://play.google.com/store/apps/details?id={APP_ID}&hl=ko&gl=KR"
        },
        {
            'headers': {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept-Language': 'ja-JP,ja;q=0.9',
                'Cache-Control': 'no-cache',
            },
            'url': f"https://play.google.com/store/apps/details?id={APP_ID}&hl=ja&gl=JP"
        },
    ]
    
    all_versions = []
    all_dates = []
    
    for idx, config in enumerate(attempts_configs):
        try:
            print(f"\n   시도 {idx + 1}/{len(attempts_configs)}")
            
            # 캐시 무효화 파라미터 추가
            timestamp = int(time.time() * 1000)
            url_with_cache_bust = f"{config['url']}&_cb={timestamp}"
            
            session = requests.Session()
            response = session.get(
                url_with_cache_bust,
                headers=config['headers'],
                timeout=20,
                allow_redirects=True
            )
            response.raise_for_status()
            
            html = response.text
            
            # 버전 추출 (여러 패턴)
            version_patterns = [
                r'"\s*Current\s+Version\s*"[^<]*?<[^>]*?>\s*([0-9]+\.[0-9]+\.[0-9]+[^<\s]*)',
                r'softwareVersion["\']?\s*:\s*["\']([0-9]+\.[0-9]+\.[0-9]+[^"\']*)["\']',
                r'\[\s*"([0-9]+\.[0-9]+\.[0-9]+)"\s*\]',
                r'versionName["\']?\s*:\s*["\']([0-9]+\.[0-9]+\.[0-9]+[^"\']*)["\']',
            ]
            
            found_version = None
            for pattern in version_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    # 유효한 버전인지 확인 (점이 2개 이상)
                    if match.count('.') >= 2:
                        found_version = match.strip()
                        print(f"      ✓ 버전 발견: {found_version}")
                        all_versions.append(found_version)
                        break
                if found_version:
                    break
            
            if not found_version:
                print(f"      ⚠️ 버전을 찾지 못함")
            
            # 날짜 추출
            date_patterns = [
                r'datePublished["\']?\s*:\s*["\']([^"\']+)["\']',
                r'Updated\s+on[^<]*?<[^>]*?>([^<]+)<',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    date_str = match.group(1).strip()
                    all_dates.append(date_str)
                    print(f"      ✓ 날짜 발견: {date_str}")
                    break
            
            time.sleep(1)  # 요청 간 대기
            
        except Exception as e:
            print(f"      ❌ 실패: {e}")
            continue
    
    # 수집된 버전들 중 가장 높은 버전 선택
    if all_versions:
        def parse_version(v):
            try:
                parts = re.findall(r'\d+', v)
                return tuple(map(int, parts[:3]))
            except:
                return (0, 0, 0)
        
        latest_version = max(all_versions, key=parse_version)
        print(f"\n   ✅ 최종 선택 버전: {latest_version}")
        print(f"   📋 모든 발견된 버전: {list(set(all_versions))}")
    else:
        latest_version = None
    
    # 날짜 처리
    if all_dates:
        date_str = all_dates[0]
        try:
            if 'T' in date_str or '-' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                pst_tz = timezone(timedelta(hours=-8))
                formatted_date = dt.astimezone(pst_tz).strftime('%Y. %m. %d')
            else:
                formatted_date = date_str
        except:
            formatted_date = date_str
    else:
        formatted_date = None
    
    return latest_version, formatted_date

def get_version_from_scraper():
    """google-play-scraper로 폴백"""
    try:
        from google_play_scraper import app
        
        print("\n📦 google-play-scraper 폴백...")
        
        # 캐시 방지: 모듈 재로드
        if 'google_play_scraper' in sys.modules:
            import importlib
            importlib.reload(sys.modules['google_play_scraper'])
        
        configs = [
            {'lang': 'en', 'country': 'us'},
            {'lang': 'en', 'country': 'gb'},
            {'lang': 'ko', 'country': 'kr'},
        ]
        
        versions = []
        dates = []
        
        for config in configs:
            try:
                result = app(APP_ID, **config)
                v = result.get('version')
                d = result.get('updated')
                
                if v and v not in ['Varies with device', '기기에 따라 다름']:
                    versions.append(v)
                    dates.append(d)
                    print(f"   ✓ {config}: {v}")
                
                time.sleep(0.5)
            except:
                continue
        
        if versions:
            # 가장 높은 버전 선택
            def parse_version(v):
                try:
                    return tuple(map(int, v.split('.')[:3]))
                except:
                    return (0, 0, 0)
            
            latest_version = max(versions, key=parse_version)
            latest_date = dates[versions.index(latest_version)]
            
            pst_tz = timezone(timedelta(hours=-8))
            formatted_date = datetime.fromtimestamp(
                latest_date, tz=timezone.utc
            ).astimezone(pst_tz).strftime('%Y. %m. %d')
            
            return latest_version, formatted_date
        
    except Exception as e:
        print(f"   ❌ 실패: {e}")
    
    return None, None

def get_app_info():
    """앱 정보 가져오기 (다중 소스)"""
    
    print("=" * 70)
    print("🔍 최신 버전 정보 수집 시작")
    print("=" * 70)
    
    # 방법 1: 웹 스크래핑
    web_version, web_date = get_version_from_web_multiple_attempts()
    
    # 방법 2: google-play-scraper
    scraper_version, scraper_date = get_version_from_scraper()
    
    print("\n" + "=" * 70)
    print("📊 수집 결과:")
    print(f"   웹: 버전={web_version}, 날짜={web_date}")
    print(f"   Scraper: 버전={scraper_version}, 날짜={scraper_date}")
    print("=" * 70)
    
    # 버전 비교하여 더 높은 것 선택
    def parse_version(v):
        if not v:
            return (0, 0, 0)
        try:
            parts = re.findall(r'\d+', v)
            return tuple(map(int, parts[:3]))
        except:
            return (0, 0, 0)
    
    final_version = None
    final_date = None
    
    if web_version and scraper_version:
        if parse_version(web_version) >= parse_version(scraper_version):
            final_version = web_version
            final_date = web_date
        else:
            final_version = scraper_version
            final_date = scraper_date
    elif web_version:
        final_version = web_version
        final_date = web_date
    elif scraper_version:
        final_version = scraper_version
        final_date = scraper_date
    
    if not final_version:
        return {
            "version": "확인 실패",
            "updated": "확인 실패"
        }
    
    print(f"\n✅ 최종 결정: 버전={final_version}, 날짜={final_date}")
    
    return {
        "version": final_version,
        "updated": final_date or "날짜 확인 실패"
    }

# 메인 실행
print("=" * 70)
print(f"🎮 던전 슬래셔 업데이트 체크")
print(f"⏰ {datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S KST')}")
print("=" * 70)

current_data = get_app_info()

print(f"\n📱 현재 플레이스토어 정보:")
print(f"   버전: {current_data['version']}")
print(f"   업데이트: {current_data['updated']}")

# 이전 상태 로드
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding='utf-8') as f:
        old_data = json.load(f)
    print(f"\n📂 저장된 이전 정보:")
    print(f"   버전: {old_data.get('version', 'N/A')}")
    print(f"   업데이트: {old_data.get('updated', 'N/A')}")
else:
    old_data = {}
    print("\n📂 이전 상태 없음 (첫 실행)")

# 변경 감지
if current_data['version'] != "확인 실패":
    version_changed = old_data.get("version") != current_data["version"]
    date_changed = old_data.get("updated") != current_data["updated"]
    
    if version_changed or date_changed:
        print("\n" + "=" * 70)
        print("🔔 변경 감지!")
        
        if version_changed:
            print(f"   📦 버전: {old_data.get('version', 'N/A')} → {current_data['version']}")
        if date_changed:
            print(f"   📅 날짜: {old_data.get('updated', 'N/A')} → {current_data['updated']}")
        
        print("=" * 70)
        
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
    print("\n⚠️ 데이터 확인 실패")

print("=" * 70)
