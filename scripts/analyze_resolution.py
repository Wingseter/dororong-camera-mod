#!/usr/bin/env python3
"""Phase 0: 해상도 진실 검증 — 촬영 결과물 분석 스크립트

SD 카드에서 각 해상도로 촬영한 사진/영상을 비교 분석하여
1080P/12M 등이 실제 해상도인지 업스케일인지 판별합니다.

사용법:
    python3 scripts/analyze_resolution.py /Volumes/SD/DCIM/
"""
import sys, os, struct
from pathlib import Path

def analyze_jpeg(path):
    """JPEG 파일에서 해상도, 파일 크기, 양자화 테이블 품질 추출"""
    with open(path, 'rb') as f:
        data = f.read()

    info = {
        'path': str(path),
        'filename': path.name,
        'size': len(data),
        'width': 0, 'height': 0,
        'qtable_avg': 0,
        'has_gpencoder': b'GPEncoder' in data,
    }

    # JPEG SOF 마커에서 해상도 추출
    i = 0
    qtables = []
    while i < len(data) - 1:
        if data[i] == 0xFF:
            marker = data[i+1]
            if marker == 0xD8:  # SOI
                i += 2
                continue
            if marker == 0x00 or marker == 0xFF:
                i += 1
                continue
            if marker == 0xD9:  # EOI
                break
            # 마커 길이
            if i + 3 < len(data):
                length = struct.unpack('>H', data[i+2:i+4])[0]
            else:
                break

            # SOF0/SOF2 (Baseline/Progressive)
            if marker in (0xC0, 0xC2):
                if i + 9 < len(data):
                    info['height'] = struct.unpack('>H', data[i+5:i+7])[0]
                    info['width'] = struct.unpack('>H', data[i+7:i+9])[0]

            # DQT (Quantization Table)
            if marker == 0xDB:
                tbl_data = data[i+4:i+2+length]
                j = 0
                while j < len(tbl_data):
                    precision = (tbl_data[j] >> 4) & 0xF
                    tbl_size = 128 if precision else 64
                    if j + 1 + tbl_size <= len(tbl_data):
                        values = list(tbl_data[j+1:j+1+tbl_size])
                        if precision == 0:
                            qtables.append(sum(values) / len(values))
                    j += 1 + tbl_size

            i += 2 + length
        else:
            i += 1

    if qtables:
        info['qtable_avg'] = sum(qtables) / len(qtables)

    return info

def analyze_avi(path):
    """AVI 파일에서 해상도, 프레임레이트, 비트레이트 추출"""
    with open(path, 'rb') as f:
        data = f.read(4096)  # 헤더만 읽기

    info = {
        'path': str(path),
        'filename': path.name,
        'size': os.path.getsize(path),
        'width': 0, 'height': 0,
        'fps': 0,
        'has_gpencoder': b'GPEncoder' in data or b'Generalplus' in data,
    }

    # AVI 헤더에서 해상도/FPS 추출
    # avih 청크 찾기
    idx = data.find(b'avih')
    if idx >= 0 and idx + 56 < len(data):
        usec_per_frame = struct.unpack('<I', data[idx+8:idx+12])[0]
        if usec_per_frame > 0:
            info['fps'] = round(1_000_000 / usec_per_frame, 1)
        info['width'] = struct.unpack('<I', data[idx+40:idx+44])[0]
        info['height'] = struct.unpack('<I', data[idx+44:idx+48])[0]

    # 비트레이트 계산
    duration = info['size'] / (info['fps'] * 1024) if info['fps'] > 0 else 0
    if duration > 0:
        info['bitrate_kbps'] = round(info['size'] * 8 / 1024 / duration, 1)

    return info

def estimate_real_resolution(jpeg_info):
    """JPEG 분석 결과에서 실제 해상도 추정

    업스케일된 이미지는:
    - 파일 크기 대비 해상도가 비정상적으로 큼
    - Q-table 품질 대비 디테일이 부족
    - bytes-per-pixel이 매우 낮음
    """
    w, h = jpeg_info['width'], jpeg_info['height']
    pixels = w * h
    if pixels == 0:
        return "분석 불가"

    bpp = jpeg_info['size'] / pixels  # bytes per pixel

    # 경험적 기준:
    # 실제 해상도: bpp > 0.3 (적당한 JPEG 압축)
    # 업스케일: bpp < 0.15 (해상도만 크고 정보 없음)
    if bpp < 0.1:
        return f"업스케일 가능성 높음 (bpp={bpp:.3f})"
    elif bpp < 0.2:
        return f"업스케일 의심 (bpp={bpp:.3f})"
    else:
        return f"실제 해상도 추정 (bpp={bpp:.3f})"

def main():
    if len(sys.argv) < 2:
        print("사용법: python3 scripts/analyze_resolution.py <DCIM 경로>")
        print("예: python3 scripts/analyze_resolution.py /Volumes/SD/DCIM/")
        sys.exit(1)

    dcim_path = Path(sys.argv[1])
    if not dcim_path.exists():
        print(f"경로 없음: {dcim_path}")
        sys.exit(1)

    jpgs = sorted(dcim_path.glob("PICT*.jpg")) + sorted(dcim_path.glob("PICT*.JPG"))
    avis = sorted(dcim_path.glob("MOVI*.avi")) + sorted(dcim_path.glob("MOVI*.AVI"))

    print("=" * 70)
    print("Phase 0: 해상도 진실 검증")
    print("=" * 70)

    if jpgs:
        print(f"\n사진 {len(jpgs)}장 분석:")
        print(f"{'파일명':<16} {'해상도':<14} {'크기':>10} {'bpp':>6} {'Q평균':>6} {'판정'}")
        print("-" * 70)

        resolution_groups = {}
        for jpg in jpgs:
            info = analyze_jpeg(jpg)
            w, h = info['width'], info['height']
            res_key = f"{w}x{h}"
            pixels = w * h
            bpp = info['size'] / pixels if pixels > 0 else 0
            verdict = estimate_real_resolution(info)

            if res_key not in resolution_groups:
                resolution_groups[res_key] = []
            resolution_groups[res_key].append(info)

            print(f"{info['filename']:<16} {res_key:<14} {info['size']:>10,} {bpp:>6.3f} {info['qtable_avg']:>6.1f} {verdict}")

        print(f"\n해상도별 요약:")
        for res, infos in sorted(resolution_groups.items(), key=lambda x: -x[1][0]['width']):
            avg_size = sum(i['size'] for i in infos) / len(infos)
            avg_bpp = avg_size / (infos[0]['width'] * infos[0]['height']) if infos[0]['width'] > 0 else 0
            print(f"  {res}: {len(infos)}장, 평균 {avg_size/1024:.0f}KB, bpp={avg_bpp:.3f}")

    if avis:
        print(f"\n영상 {len(avis)}개 분석:")
        print(f"{'파일명':<16} {'해상도':<14} {'크기':>12} {'FPS':>6} {'인코더'}")
        print("-" * 70)
        for avi in avis:
            info = analyze_avi(avi)
            res = f"{info['width']}x{info['height']}"
            enc = "GPEncoder" if info['has_gpencoder'] else "Unknown"
            print(f"{info['filename']:<16} {res:<14} {info['size']:>12,} {info['fps']:>6.1f} {enc}")

    if not jpgs and not avis:
        print("PICT*.jpg 또는 MOVI*.avi 파일을 찾을 수 없습니다.")
        print(f"검색 경로: {dcim_path}")

    print(f"\n{'='*70}")
    print("테스트 방법:")
    print("  1. 카메라 메뉴에서 해상도를 각각 바꿔가며 동일 피사체 촬영")
    print("  2. 사진: 12M → 8M → 2M → 1M → VGA (각 1장씩)")
    print("  3. 영상: 1080P → 720P → VGA (각 2초씩)")
    print("  4. SD 카드를 Mac에 꽂고 이 스크립트 실행")
    print("  5. bpp(bytes-per-pixel)가 낮으면 업스케일 가능성 높음")

if __name__ == '__main__':
    main()
