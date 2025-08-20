#!/usr/bin/env python3
"""
하이브리드 GPS + Google API 통합 테스트
"""

import time
import os
from datetime import datetime

def test_hybrid_gps_system():
    """하이브리드 GPS 시스템 테스트"""
    
    print("🧪 하이브리드 GPS + Google API 통합 테스트")
    print("=" * 50)
    
    try:
        from gps.hybrid_gps import init_hybrid_gps, read_hybrid_location, get_location_status, cleanup_hybrid_gps
        
        # 1. 시스템 초기화
        print("1️⃣ 하이브리드 GPS 시스템 초기화...")
        gps_system = init_hybrid_gps()
        print("✅ 초기화 완료")
        
        # 2. 시스템 상태 확인
        print("\n2️⃣ 시스템 상태 확인...")
        status = get_location_status()
        for key, value in status.items():
            print(f"   {key}: {value}")
        
        # 3. 위치 정보 획득 테스트
        print("\n3️⃣ 위치 정보 획득 테스트...")
        print("   위치 정보 획득 중... (최대 10초 대기)")
        
        start_time = time.time()
        location = None
        
        # 최대 10초 동안 위치 정보 획득 시도
        while time.time() - start_time < 10:
            location = read_hybrid_location()
            if location:
                break
            time.sleep(1)
        
        if location:
            print("✅ 위치 정보 획득 성공!")
            print(f"   위도: {location.latitude:.6f}")
            print(f"   경도: {location.longitude:.6f}")
            print(f"   고도: {location.altitude:.1f}m" if location.altitude else "   고도: N/A")
            print(f"   정확도: {location.accuracy:.1f}m" if location.accuracy else "   정확도: N/A")
            print(f"   소스: {location.source.value}")
            print(f"   시간: {location.timestamp}")
            
            # 정확도 평가
            if location.accuracy:
                if location.accuracy <= 20:
                    print("   평가: 🟢 매우 정확 (GPS 수준)")
                elif location.accuracy <= 100:
                    print("   평가: 🟡 정확 (Google API 수준)")
                elif location.accuracy <= 500:
                    print("   평가: 🟠 보통 (개선된 WiFi 수준)")
                else:
                    print("   평가: 🔴 부정확")
        else:
            print("❌ 위치 정보 획득 실패")
        
        # 4. Google API 테스트
        print("\n4️⃣ Google API 통합 테스트...")
        try:
            # WiFi 위치만 테스트
            wifi_location = gps_system.get_wifi_location()
            if wifi_location:
                print("✅ Google WiFi 위치 추정 성공!")
                print(f"   위치: {wifi_location.latitude:.6f}, {wifi_location.longitude:.6f}")
                print(f"   정확도: {wifi_location.accuracy:.1f}m")
                print(f"   소스: {wifi_location.source.value}")
            else:
                print("❌ Google WiFi 위치 추정 실패")
        except Exception as e:
            print(f"❌ Google API 테스트 오류: {e}")
        
        # 5. 정리
        print("\n5️⃣ 시스템 정리...")
        cleanup_hybrid_gps()
        print("✅ 정리 완료")
        
        return True
        
    except Exception as e:
        print(f"❌ 하이브리드 GPS 테스트 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_accuracy_comparison():
    """정확도 비교 테스트"""
    print("\n📊 정확도 비교 테스트")
    print("=" * 30)
    
    try:
        from gps.hybrid_gps import init_hybrid_gps, cleanup_hybrid_gps
        
        gps_system = init_hybrid_gps()
        
        # GPS 위치 테스트
        print("🔍 GPS 위치 테스트...")
        gps_location = gps_system.get_gps_location()
        if gps_location:
            print(f"   GPS 정확도: {gps_location.accuracy:.1f}m")
        else:
            print("   GPS: 사용 불가")
        
        # WiFi 위치 테스트
        print("🔍 WiFi 위치 테스트...")
        wifi_location = gps_system.get_wifi_location()
        if wifi_location:
            print(f"   WiFi 정확도: {wifi_location.accuracy:.1f}m")
        else:
            print("   WiFi: 사용 불가")
        
        # 하이브리드 위치 테스트
        print("🔍 하이브리드 위치 테스트...")
        hybrid_location = gps_system.get_hybrid_location()
        if hybrid_location:
            print(f"   하이브리드 정확도: {hybrid_location.accuracy:.1f}m")
        else:
            print("   하이브리드: 사용 불가")
        
        cleanup_hybrid_gps()
        
    except Exception as e:
        print(f"❌ 정확도 비교 테스트 오류: {e}")

if __name__ == "__main__":
    print("🚀 CANSAT HEPHAESTUS 2025 - 하이브리드 GPS 테스트")
    print("=" * 60)
    
    # Google API 키 확인
    api_key = os.getenv('GOOGLE_MAPS_API_KEY', 'AIzaSyBa2R_xba0AbZf5w-AcpgbYpotqJ5on7_s')
    print(f"🔑 Google API 키: {api_key[:10]}...")
    
    # 하이브리드 GPS 테스트
    if test_hybrid_gps_system():
        print("\n🎉 하이브리드 GPS 시스템 테스트 완료!")
        
        # 정확도 비교 테스트
        test_accuracy_comparison()
        
        print("\n📈 성능 요약:")
        print("   • GPS: 3m ~ 20m 정확도 (실외에서만)")
        print("   • Google API: 10m ~ 100m 정확도 (인터넷 필요)")
        print("   • 개선된 WiFi: 50m ~ 500m 정확도 (오프라인 가능)")
        print("   • 하이브리드: 최적 조합으로 최고 정확도")
        
    else:
        print("\n❌ 하이브리드 GPS 시스템 테스트 실패")
        print("하드웨어 연결과 API 키를 확인하세요.")
