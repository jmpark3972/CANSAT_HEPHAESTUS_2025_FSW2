#!/usr/bin/env python3
"""
Google Maps API 키 테스트 스크립트
"""

import os
import requests
import json

def test_google_api():
    """Google Maps API 키 테스트"""
    
    # API 키 설정
    api_key = "AIzaSyBa2R_xba0AbZf5w-AcpgbYpotqJ5on7_s"
    
    print("🔑 Google Maps API 키 테스트")
    print("=" * 40)
    print(f"API 키: {api_key[:10]}...")
    
    # 테스트용 WiFi 데이터
    test_payload = {
        'wifiAccessPoints': [
            {
                'macAddress': '00:11:22:33:44:55',
                'signalStrength': -50,
                'signalToNoiseRatio': 40
            },
            {
                'macAddress': 'AA:BB:CC:DD:EE:FF',
                'signalStrength': -60,
                'signalToNoiseRatio': 35
            }
        ]
    }
    
    try:
        print("🌐 Google Geolocation API 호출 중...")
        
        response = requests.post(
            f'https://www.googleapis.com/geolocation/v1/geolocate?key={api_key}',
            json=test_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            location = data['location']
            accuracy = data.get('accuracy', 'N/A')
            
            print("✅ API 키 테스트 성공!")
            print(f"   위치: {location['lat']:.6f}, {location['lng']:.6f}")
            print(f"   정확도: {accuracy}m")
            print(f"   평가: {'🟢 매우 정확' if accuracy <= 50 else '🟡 정확' if accuracy <= 100 else '🟠 보통'}")
            
            return True
        else:
            print(f"❌ API 키 테스트 실패: {response.status_code}")
            print(f"   오류: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API 키 테스트 오류: {e}")
        return False

def test_hybrid_gps():
    """하이브리드 GPS 테스트"""
    print("\n🧪 하이브리드 GPS 테스트")
    print("=" * 40)
    
    try:
        from gps.hybrid_gps import init_hybrid_gps, read_hybrid_location, cleanup_hybrid_gps
        
        # 하이브리드 GPS 시스템 초기화
        gps_system = init_hybrid_gps()
        print("✅ 하이브리드 GPS 시스템 초기화 완료")
        
        # 위치 정보 획득
        location = read_hybrid_location()
        
        if location:
            print("✅ 위치 정보 획득 성공!")
            print(f"   위도: {location.latitude:.6f}")
            print(f"   경도: {location.longitude:.6f}")
            print(f"   고도: {location.altitude:.1f}m" if location.altitude else "   고도: N/A")
            print(f"   정확도: {location.accuracy:.1f}m" if location.accuracy else "   정확도: N/A")
            print(f"   소스: {location.source.value}")
            print(f"   시간: {location.timestamp}")
        else:
            print("❌ 위치 정보 획득 실패")
        
        # 정리
        cleanup_hybrid_gps()
        
    except Exception as e:
        print(f"❌ 하이브리드 GPS 테스트 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Google API 테스트
    if test_google_api():
        print("\n🎉 Google Maps API가 정상 작동합니다!")
        
        # 하이브리드 GPS 테스트
        test_hybrid_gps()
    else:
        print("\n❌ Google Maps API에 문제가 있습니다.")
        print("API 키와 Geolocation API 활성화를 확인하세요.")
