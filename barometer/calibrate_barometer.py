def test_load_offset2():
    offset2 = load_offset()

    if offset2 is None:
        print("❗ offset2 (보정값) 파일이 존재하지 않습니다. 기본값 0으로 설정합니다.")
        offset2 = 0.0
    else:
        print(f"✅ offset2 로드됨: {offset2:.2f} m")

    return offset2

if __name__ == "__main__":
    test_offset = test_load_offset2()
    print(f"지금 불러온 offset2 = {test_offset}")