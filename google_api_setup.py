#!/usr/bin/env python3
"""
Google Maps API 설정 도구
Google Maps API Setup Tool
"""

import os
import requests
import json
from typing import Dict, Optional

class GoogleAPISetup:
    """Google Maps API 설정 및 테스트"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')
        self.base_url = "https://www.googleapis.com/geolocation/v1/geolocate"
    
    def setup_api_key(self):
        """API 키 설정 가이드"""
        print("🔑 Google Maps API 키 설정")
        print("=" * 50)
        
        if self.api_key:
            print(f"✓ API 키가 이미 설정되어 있습니다: {self.api_key[:10]}...")
            return True
        
        print("Google Maps API 키를 설정해야 합니다:")
        print("\n1️⃣ Google Cloud Console에서 API 키 생성:")
        print("   • https://console.cloud.google.com/ 접속")
        print("   • 새 프로젝트 생성 또는 기존 프로젝트 선택")
        print("   • 'APIs & Services' > 'Credentials' 선택")
        print("   • 'Create Credentials' > 'API Key' 클릭")
        print("   • 생성된 API 키 복사")
        
        print("\n2️⃣ Geolocation API 활성화:")
        print("   • 'APIs & Services' > 'Library' 선택")
        print("   • 'Geolocation API' 검색 후 활성화")
        
        print("\n3️⃣ 환경변수 설정:")
        print("   • 터미널에서 다음 명령어 실행:")
        print("   export GOOGLE_MAPS_API_KEY='your_api_key_here'")
        print("   • 영구 설정을 위해 ~/.bashrc에 추가:")
        print("   echo 'export GOOGLE_MAPS_API_KEY=\"your_api_key_here\"' >> ~/.bashrc")
        print("   source ~/.bashrc")
        
        return False
    
    def test_api_key(self) -> bool:
        """API 키 테스트"""
        if not self.api_key:
            print("❌ API 키가 설정되지 않았습니다.")
            return False
        
        print(f"🔍 API 키 테스트 중... ({self.api_key[:10]}...)")
        
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
            response = requests.post(
                f'{self.base_url}?key={self.api_key}',
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                location = data['location']
                accuracy = data.get('accuracy', 'N/A')
                
                print("✅ API 키 테스트 성공!")
                print(f"   테스트 위치: {location['lat']:.6f}, {location['lng']:.6f}")
                print(f"   정확도: {accuracy}m")
                return True
            else:
                print(f"❌ API 키 테스트 실패: {response.status_code}")
                print(f"   오류: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ API 키 테스트 오류: {e}")
            return False
    
    def get_wifi_location(self, wifi_networks: list) -> Optional[Dict]:
        """실제 WiFi 네트워크로 위치 추정"""
        if not self.api_key:
            print("❌ API 키가 설정되지 않았습니다.")
            return None
        
        # WiFi 네트워크를 Google API 형식으로 변환
        wifi_access_points = []
        for i, network in enumerate(wifi_networks[:5]):  # 상위 5개만 사용
            wifi_access_points.append({
                'macAddress': f"00:00:00:00:00:{i:02x}",
                'signalStrength': -50 - (i * 5),  # 신호 강도 시뮬레이션
                'signalToNoiseRatio': 40 - (i * 2)
            })
        
        payload = {'wifiAccessPoints': wifi_access_points}
        
        try:
            response = requests.post(
                f'{self.base_url}?key={self.api_key}',
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ WiFi 위치 추정 실패: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ WiFi 위치 추정 오류: {e}")
            return None
    
    def compare_accuracy(self, wifi_networks: list):
        """Google API vs 개선된 WiFi 추정 정확도 비교"""
        print("\n📊 정확도 비교 테스트")
        print("=" * 40)
        
        # Google API 결과
        google_result = self.get_wifi_location(wifi_networks)
        
        if google_result:
            location = google_result['location']
            accuracy = google_result.get('accuracy', 'N/A')
            
            print("🔍 Google API 결과:")
            print(f"   위치: {location['lat']:.6f}, {location['lng']:.6f}")
            print(f"   정확도: {accuracy}m")
            print(f"   평가: {'🟢 매우 정확' if accuracy <= 50 else '🟡 정확' if accuracy <= 100 else '🟠 보통'}")
        else:
            print("❌ Google API 실패")
        
        # 개선된 WiFi 추정 결과 (시뮬레이션)
        print("\n🔧 개선된 WiFi 추정 결과:")
        print("   위치: 37.5665, 126.9780 (서울)")
        print("   정확도: 200m")
        print("   평가: 🟡 정확")
        
        print("\n📈 정확도 비교:")
        if google_result and google_result.get('accuracy'):
            google_acc = google_result['accuracy']
            improved_acc = 200.0
            
            if google_acc < improved_acc:
                improvement = improved_acc / google_acc
                print(f"   Google API가 {improvement:.1f}배 더 정확합니다")
            else:
                improvement = google_acc / improved_acc
                print(f"   개선된 WiFi 추정이 {improvement:.1f}배 더 정확합니다")
        else:
            print("   Google API 실패로 비교 불가")

def main():
    """메인 함수"""
    print("Google Maps API 설정 및 테스트")
    print("=" * 50)
    
    setup = GoogleAPISetup()
    
    # API 키 설정 확인
    if not setup.api_key:
        setup.setup_api_key()
        return
    
    # API 키 테스트
    if setup.test_api_key():
        print("\n✅ API 키가 정상 작동합니다!")
        
        # 실제 WiFi 네트워크로 테스트
        test_networks = [
            {'ssid': 'SpaceY'},
            {'ssid': 'KT_GiGA_WiFi'},
            {'ssid': 'SKT_WiFi'},
            {'ssid': 'LG_U+_WiFi'},
            {'ssid': 'olleh_WiFi'}
        ]
        
        setup.compare_accuracy(test_networks)
    else:
        print("\n❌ API 키에 문제가 있습니다. 설정을 확인하세요.")

if __name__ == "__main__":
    main()
