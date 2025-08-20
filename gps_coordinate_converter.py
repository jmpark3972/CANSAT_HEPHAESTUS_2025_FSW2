#!/usr/bin/env python3
"""
GPS 좌표 변환 및 해석 도구
GPS Coordinate Converter and Interpreter
"""

import math
from typing import Tuple, Dict

def decimal_to_dms(decimal_degrees: float) -> Tuple[int, int, float]:
    """
    십진수 좌표를 도-분-초 형식으로 변환
    
    Args:
        decimal_degrees: 십진수 좌표 (예: 37.5665)
    
    Returns:
        (도, 분, 초) 튜플
    """
    degrees = int(decimal_degrees)
    minutes_decimal = abs(decimal_degrees - degrees) * 60
    minutes = int(minutes_decimal)
    seconds = (minutes_decimal - minutes) * 60
    
    return degrees, minutes, seconds

def dms_to_decimal(degrees: int, minutes: int, seconds: float) -> float:
    """
    도-분-초 형식을 십진수 좌표로 변환
    
    Args:
        degrees: 도
        minutes: 분
        seconds: 초
    
    Returns:
        십진수 좌표
    """
    return degrees + (minutes / 60.0) + (seconds / 3600.0)

def interpret_coordinates(latitude: float, longitude: float) -> Dict:
    """
    GPS 좌표 해석 및 정보 제공
    
    Args:
        latitude: 위도 (십진수)
        longitude: 경도 (십진수)
    
    Returns:
        좌표 정보 딕셔너리
    """
    # 도-분-초 변환
    lat_deg, lat_min, lat_sec = decimal_to_dms(abs(latitude))
    lon_deg, lon_min, lon_sec = decimal_to_dms(abs(longitude))
    
    # 방향 결정
    lat_dir = "N" if latitude >= 0 else "S"
    lon_dir = "E" if longitude >= 0 else "W"
    
    # 정밀도 계산
    lat_precision = len(str(latitude).split('.')[-1]) if '.' in str(latitude) else 0
    lon_precision = len(str(longitude).split('.')[-1]) if '.' in str(longitude) else 0
    
    # 정확도 추정 (미터 단위)
    lat_accuracy = 111000 / (10 ** lat_precision)  # 위도 1도 ≈ 111km
    lon_accuracy = 111000 * math.cos(math.radians(abs(latitude))) / (10 ** lon_precision)
    
    # 지역 추정 (한국 기준)
    region = estimate_korean_region(latitude, longitude)
    
    return {
        'decimal': {
            'latitude': latitude,
            'longitude': longitude
        },
        'dms': {
            'latitude': f"{lat_deg}° {lat_min}' {lat_sec:.2f}\" {lat_dir}",
            'longitude': f"{lon_deg}° {lon_min}' {lon_sec:.2f}\" {lon_dir}"
        },
        'precision': {
            'latitude_decimal_places': lat_precision,
            'longitude_decimal_places': lon_precision
        },
        'accuracy': {
            'latitude_meters': lat_accuracy,
            'longitude_meters': lon_accuracy,
            'estimated_total_accuracy': max(lat_accuracy, lon_accuracy)
        },
        'region': region
    }

def estimate_korean_region(latitude: float, longitude: float) -> str:
    """
    한국 지역 추정 (대략적)
    """
    if 33.0 <= latitude <= 38.5 and 124.0 <= longitude <= 132.0:
        # 주요 도시 근사치
        if 37.4 <= latitude <= 37.7 and 126.8 <= longitude <= 127.2:
            return "서울특별시"
        elif 35.1 <= latitude <= 35.2 and 129.0 <= longitude <= 129.1:
            return "부산광역시"
        elif 35.8 <= latitude <= 35.9 and 128.5 <= longitude <= 128.6:
            return "대구광역시"
        elif 35.1 <= latitude <= 35.2 and 126.8 <= longitude <= 126.9:
            return "광주광역시"
        elif 37.4 <= latitude <= 37.5 and 127.1 <= longitude <= 127.2:
            return "경기도 (수원/성남)"
        elif 35.1 <= latitude <= 35.2 and 126.8 <= longitude <= 126.9:
            return "전라남도"
        elif 35.8 <= latitude <= 35.9 and 128.5 <= longitude <= 128.6:
            return "경상북도"
        else:
            return "한국 (정확한 지역은 지도 확인 필요)"
    else:
        return "한국 외 지역"

def format_coordinate_info(latitude: float, longitude: float) -> str:
    """
    좌표 정보를 보기 좋게 포맷팅
    """
    info = interpret_coordinates(latitude, longitude)
    
    result = f"""
📍 GPS 좌표 해석 결과
{'='*40}

📊 좌표 정보:
  십진수: {info['decimal']['latitude']:.6f}, {info['decimal']['longitude']:.6f}
  도분초: {info['dms']['latitude']}, {info['dms']['longitude']}

🎯 정밀도:
  위도 소수점 자릿수: {info['precision']['latitude_decimal_places']}자리
  경도 소수점 자릿수: {info['precision']['longitude_decimal_places']}자리

📏 추정 정확도:
  위도 정확도: 약 {info['accuracy']['latitude_meters']:.1f}m
  경도 정확도: 약 {info['accuracy']['longitude_meters']:.1f}m
  전체 정확도: 약 {info['accuracy']['estimated_total_accuracy']:.1f}m

🗺️  추정 지역: {info['region']}

💡 참고사항:
  • 소수점 1자리: 약 11km 정확도
  • 소수점 2자리: 약 1.1km 정확도
  • 소수점 3자리: 약 110m 정확도
  • 소수점 4자리: 약 11m 정확도
  • 소수점 5자리: 약 1.1m 정확도
  • 소수점 6자리: 약 11cm 정확도
"""
    return result

def main():
    """메인 함수 - 예시 좌표들 테스트"""
    print("GPS 좌표 변환 및 해석 도구")
    print("=" * 50)
    
    # 테스트 좌표들
    test_coordinates = [
        (37.5665, 126.9780, "서울시청"),
        (35.1796, 129.0756, "부산시청"),
        (35.8714, 128.6014, "대구시청"),
        (37.4563, 126.7052, "인천시청"),
        (35.1595, 126.8526, "광주시청")
    ]
    
    for lat, lon, name in test_coordinates:
        print(f"\n🏛️ {name} 좌표:")
        print(format_coordinate_info(lat, lon))
        print("-" * 50)
    
    # 사용자 입력 받기
    print("\n🔍 직접 좌표 입력하기")
    try:
        lat = float(input("위도를 입력하세요 (예: 37.5665): "))
        lon = float(input("경도를 입력하세요 (예: 126.9780): "))
        
        print(format_coordinate_info(lat, lon))
        
    except ValueError:
        print("올바른 숫자를 입력해주세요.")
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")

if __name__ == "__main__":
    main()
