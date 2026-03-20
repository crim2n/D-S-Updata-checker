import os
import json
import requests
from datetime import datetime, timezone, timedelta
import time

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "state.json"
APP_ID = "com.nspgames.dungeonslasher"
URL = f"https://play.google.com/store/apps/details?id={APP_ID}&hl=ko&gl=KR"

def get_app_info_multi_region():
    """여러 지역에서 정보를 가져와 교차 검증"""
    try:
        from google_play_scraper import app
        
        print("📦 다중 지역 정보 수집 중...")
        
        regions = [
            {'lang': 'en', 'country': 'us', 'name': '미국'},
            {'lang': 'en', 'country': 'gb', 'name': '영국'},
            {'lang': 'ko', 'country': 'kr', 'name': '한국'},
            {'lang': 'ja', 'country': 'jp', 'name': '일본'},
        ]
        
        results = []
        
        for region in regions:
            try:
                print(f"   {region['name']} 확인 중...")
                result = app(APP_ID, lang=region['lang'], country=region['country'])
                
                version = result.get('version', '')
                updated_ts = result.get('updated', 0)
                
                if version and version not in ['Varies with device', '기기에 따라 다름']:
                    results.append({
                        'version': version,
                        'timestamp': updated_ts,
                        'region': region['name']
                    })
                    print(f"      ✓ 버전: {version}, TS: {updated_ts}")
                else:
                    print(f"      ⚠️ 유효하지 않은 버전: {version}")
                
                time.sleep(0.5)  # API 제한 방지
                
            except Exception as e:
                print(f"      ❌ 실패: {e}")
                continue
        
        if not results:
            print("   ❌ 모든 지역에서 실패")
            return None
        
        # 가장 최신 타임스탬프를 가진 결과 선택
        latest = max(results, key=lambda x: x['timestamp'])
        
        print(f"\n   ✅ 최신 데이터: {latest['region']}")
        print(f"      버전: {latest['version']}")
        print(f"      타임스탬프: {latest['timestamp']}")
        
        # 날짜 포맷팅
        pst_tz = timezone(timedelta(hours=-8))
        updated = datetime.fromtimestamp(
            latest['timestamp'], 
            tz=timezone.utc
        ).astimezone(pst_tz).strftime('%Y. %m. %d')
        
        # 모든 지역의 버전 수집 (디버깅용)
        all_versions = list(set([r['version'] for r in results]))
        
        return {
            "version": latest['version'],
            "updated": updated,
            "timestamp": latest['timestamp'],
            "all_versions": all_versions,
            "check_count": 0  # 연속 확인 횟수
        }
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return None

def parse_version(version_str):
    """버전 문자열을 비교 가능한 튜플로 변환"""
    try:
        parts = version_str.split('.')
        return tuple(int(p) for p in parts[:3])
    except:
        return (0, 0, 0)

# 메인 실행
print("=" * 70)
print(f"🎮 던전 슬래셔 업데이트 체크")
kst = timezone(timedelta(hours=9))
now = datetime.now(kst)
print(f"⏰ 실행: {now.strftime('%Y-%m-%d %H:%M:%S KST')}")
print("=" * 70)

# 정보 가져오기
current_data = get_app_info_multi_region()

if not current_data:
    print("❌ 데이터 수집 실패")
    exit(1)

print(f"\n📱 현재 플레이스토어:")
print(f"   버전: {current_data['version']}")
print(f"   날짜: {current_data['updated']}")
print(f"   타임스탬프: {current_data['timestamp']}")
if len(current_data['all_versions']) > 1:
    print(f"   ⚠️ 지역별 버전 차이: {current_data['all_versions']}")

# 이전 상태 로드
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding='utf-8') as f:
        old_data = json.load(f)
    print(f"\n📂 이전 저장 데이터:")
    print(f"   버전: {old_data.get('version', 'N/A')}")
    print(f"   날짜: {old_data.get('updated', 'N/A')}")
    print(f"   타임스탬프: {old_data.get('timestamp', 'N/A')}")
    print(f"   확인 횟수: {old_data.get('check_count', 0)}")
else:
    old_data = {}
    print("\n📂 첫 실행 (이전 데이터 없음)")

# 변경 감지 로직
version_changed = old_data.get("version") != current_data["version"]
date_changed = old_data.get("updated") != current_data["updated"]
timestamp_changed = old_data.get("timestamp") != current_data["timestamp"]

# 핫픽스 감지: 같은 날짜지만 타임스탬프가 다른 경우
is_hotfix = (not date_changed) and timestamp_changed and version_changed

# 같은 날짜, 같은 버전이 연속 5회 이상 확인되면 강제 재확인
check_count = old_data.get('check_count', 0)
force_recheck = False

if not version_changed and not date_changed:
    check_count += 1
    current_data['check_count'] = check_count
    
    # 5회마다 강제로 다시 체크 (약 1시간 40분마다)
    if check_count % 5 == 0:
        force_recheck = True
        print(f"\n🔄 연속 {check_count}회 동일 - 강제 재확인 모드")
else:
    current_data['check_count'] = 0

# 알림 조건
should_notify = version_changed or date_changed or timestamp_changed or force_recheck

if should_notify:
    print("\n" + "=" * 70)
    
    if is_hotfix:
        print("🔥 핫픽스 감지! (같은 날 버전 변경)")
    elif force_recheck:
        print("🔄 강제 재확인")
    else:
        print("🔔 업데이트 감지!")
    
    if version_changed:
        old_ver = old_data.get('version', '없음')
        new_ver = current_data['version']
        
        # 버전 비교
        old_tuple = parse_version(old_ver) if old_ver != '없음' else (0, 0, 0)
        new_tuple = parse_version(new_ver)
        
        if new_tuple > old_tuple:
            print(f"   📦 버전 업그레이드: {old_ver} → {new_ver}")
        elif new_tuple < old_tuple:
            print(f"   ⚠️ 버전 다운그레이드?: {old_ver} → {new_ver}")
        else:
            print(f"   📦 버전 변경: {old_ver} → {new_ver}")
    
    if date_changed:
        print(f"   📅 날짜: {old_data.get('updated', '없음')} → {current_data['updated']}")
    
    if timestamp_changed and not date_changed:
        print(f"   ⏱️ 타임스탬프: {old_data.get('timestamp', 0)} → {current_data['timestamp']}")
        print(f"      (같은 날짜이지만 시간이 다름 - 핫픽스 가능성)")
    
    print("=" * 70)
    
    # Discord 알림
    if is_hotfix:
        emoji = "🔥"
        title = "핫픽스 감지"
    elif force_recheck:
        emoji = "🔄"
        title = "재확인 알림"
    else:
        emoji = "🔥"
        title = "업데이트 감지"
    
    msg = (
        f"{emoji} 던전 슬래셔 {title}!\n"
        f"📦 버전: {current_data['version']}\n"
        f"📅 업데이트 날짜: {current_data['updated']}\n"
    )
    
    if is_hotfix:
        msg += f"⚠️ 같은 날 핫픽스 업데이트\n"
    
    if len(current_data['all_versions']) > 1:
        msg += f"ℹ️ 지역별 버전: {', '.join(current_data['all_versions'])}\n"
    
    msg += f"\n{URL}"
    
    try:
        response = requests.post(WEBHOOK, json={"content": msg}, timeout=10)
        response.raise_for_status()
        print("✅ Discord 알림 전송 완료")
    except Exception as e:
        print(f"⚠️ Discord 알림 실패: {e}")
    
    # 상태 저장
    with open(STATE_FILE, "w", encoding='utf-8') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)
    print("💾 상태 저장 완료")
    
else:
    print("\n✨ 변경 없음")
    
    # 변경 없어도 check_count 업데이트
    with open(STATE_FILE, "w", encoding='utf-8') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)

print("=" * 70)
