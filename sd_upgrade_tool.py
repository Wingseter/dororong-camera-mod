import sys
import os

def main():
    if len(sys.argv) < 2:
        print("사용법: python3 sd_upgrade_tool.py <펌웨어.bin>")
        sys.exit(1)
        
    filepath = sys.argv[1]
    if not os.path.isfile(filepath):
        print(f"에러: 파일 '{filepath}'을(를) 찾을 수 없습니다.")
        sys.exit(1)

    with open(filepath, 'rb') as f:
        data = f.read()
        
    # 파일 바이트 전체를 단순 합산하여 32비트 체크섬 계산 (FUN_00041678과 동일한 로직)
    file_sum = sum(data) & 0xFFFFFFFF
    
    # 펌웨어 바이너리상의 빌드 문자열(13바이트)과 다른 문자열을 주입하여 버전 체크 우회
    # 현재 기기에 설치된 빌드 문자열: "2025004291200"
    build_str = "2025004291201" 
    
    # 체크섬을 8자리 영문 대문자 헥스 문자열로 변환
    checksum_str = f"{file_sum:08X}"
    
    # 최종 파일명 조합
    # JH_5307_ (8자) + 빌드문자열 (13자) + 체크섬 (8자) + .bin (4자)
    new_filename = f"JH_5307_{build_str}{checksum_str}.bin"
    
    print("================================")
    print(" 펌웨어 SD 카드 업그레이드 도구")
    print("================================")
    print(f"입력 파일    : {filepath}")
    print(f"파일 크기    : {len(data)} 바이트")
    print(f"계산된 체크섬: 0x{checksum_str}\n")
    print("[ SD 카드 업그레이드 방법 ]")
    print(f"1. 변경된 펌웨어 파일의 이름을 아래와 같이 정확히 변경하세요:")
    print(f"   => {new_filename}")
    print(f"2. 위 파일을 SD 카드의 최상위 경로(루트)에 복사하세요.")
    print(f"3. 기기에 SD 카드를 넣고 전원을 켜면 업그레이드가 진행됩니다.")
    print(f"4. 체크섬 불일치 에러('Program error') 없이 통과합니다.")

if __name__ == '__main__':
    main()
