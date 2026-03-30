# 시작/종료 화면 교체 가이드

> 일시: 2026-03-30
> 대상: GP1235 펌웨어 160x80 LCD 화면 리소스

## 개요

카메라 전원 ON/OFF 시 LCD에 표시되는 화면을 커스텀 이미지로 교체하는 방법.

## 리소스 위치

| 화면 | 펌웨어 오프셋 | 원본 크기 | 최대 크기 | 내용 |
|------|-------------|----------|----------|------|
| **시작 (WELCOME)** | `0x0AA000` | 2,285 B | 2,560 B | "WELCOME" 텍스트 |
| **종료 (GOODBYE)** | `0x0A9600` | 2,210 B | 2,560 B | "GOODBYE" 텍스트 |

- 포맷: **JPEG**, 해상도 **160x80 픽셀**
- JPEG 데이터 끝(FFD9) 이후는 `0xFF` 패딩으로 채워짐
- 원본 추출 파일: `analysis/extracted_resources/160x80_resource3_0x0aa000.jpg` (시작), `160x80_resource2_0x0a9600.jpg` (종료)

## 이미지 제작 규격

| 항목 | 요구사항 |
|------|---------|
| 해상도 | **160x80** 픽셀 (정확히 일치해야 함) |
| 포맷 | JPEG (Baseline, non-progressive) |
| 파일 크기 | **최대 2,560 바이트** (패딩 포함 여유 공간까지) |
| 색공간 | RGB (YCbCr 서브샘플링 4:2:0 권장) |
| 배경 권장 | 어두운 배경 (LCD가 작으므로 고대비 텍스트/아이콘 권장) |

### 크기 맞추기 팁

160x80 JPEG를 2.5KB 이하로 만들려면:
- JPEG 품질 70~85 범위 사용
- 단순한 디자인 (그래디언트, 솔리드 배경 + 텍스트)
- 복잡한 사진은 압축 후 크기 초과 위험

### 이미지 생성 예시 (Python + Pillow)

```python
from PIL import Image, ImageDraw, ImageFont
import io

img = Image.new("RGB", (160, 80), (20, 20, 20))
draw = ImageDraw.Draw(img)

# 텍스트 렌더링
font = ImageFont.truetype("arial.ttf", 20)
draw.text((30, 25), "DORORONG", fill=(255, 255, 255), font=font)

# 크기 확인하며 품질 조절
for q in range(90, 10, -5):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=q)
    if buf.tell() <= 2560:
        print(f"Quality {q}: {buf.tell()} bytes")
        break

# 저장
with open("custom_welcome.jpg", "wb") as f:
    f.write(buf.getvalue())
```

### 이미지 생성 예시 (FFmpeg)

```bash
# 160x80 검은 배경에 흰 텍스트
ffmpeg -f lavfi -i "color=c=black:s=160x80:d=1" \
  -vf "drawtext=text='DORORONG':fontsize=20:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2" \
  -frames:v 1 -q:v 5 custom_welcome.jpg
```

## 적용 방법

### 방법 1: settings_patch.py 사용 (시작 화면만 — 기존 도구)

```bash
python scripts/settings_patch.py analysis/GP1235_firmware.bin --brand v1.0
```

이 도구는 시작 화면(WELCOME)만 "DORORONG / custom fw vX.X"로 자동 생성.
종료 화면(GOODBYE)은 미지원 — 수동 패치 필요.

### 방법 2: 수동 바이너리 패치 (양쪽 모두)

```python
import struct

with open("GP1235_firmware.bin", "rb") as f:
    data = bytearray(f.read())

# 커스텀 JPEG 로드
with open("custom_welcome.jpg", "rb") as f:
    welcome_jpg = f.read()

with open("custom_goodbye.jpg", "rb") as f:
    goodbye_jpg = f.read()

# 크기 검증
WELCOME_OFFSET = 0x0AA000
GOODBYE_OFFSET = 0x0A9600
MAX_SIZE = 2560  # 패딩 포함 최대

assert len(welcome_jpg) <= MAX_SIZE, f"시작 화면 JPEG 초과: {len(welcome_jpg)} > {MAX_SIZE}"
assert len(goodbye_jpg) <= MAX_SIZE, f"종료 화면 JPEG 초과: {len(goodbye_jpg)} > {MAX_SIZE}"

# GPNV XOR 차분 업데이트를 위해 변경 전 워드 기록
word_changes = []

def patch_jpeg(data, offset, jpeg_data, max_size):
    """JPEG 데이터를 펌웨어에 패치 (0xFF 패딩)"""
    padded = jpeg_data + b"\xFF" * (max_size - len(jpeg_data))
    changes = []
    for i in range(0, max_size, 4):
        abs_off = offset + i
        old_word = struct.unpack_from("<I", data, abs_off)[0]
        new_word = struct.unpack_from("<I", padded, i)[0]
        if old_word != new_word:
            changes.append((abs_off, old_word, new_word))
        struct.pack_into("<I", data, abs_off, new_word)
    return changes

# 시작 화면 패치
word_changes += patch_jpeg(data, WELCOME_OFFSET, welcome_jpg, MAX_SIZE)
# 종료 화면 패치
word_changes += patch_jpeg(data, GOODBYE_OFFSET, goodbye_jpg, MAX_SIZE)

# GPNV XOR 차분 업데이트
# 주의: WELCOME (0x0AA000)은 GPNV XOR 범위 밖 → 무시됨
# GOODBYE (0x0A9600)는 GPNV XOR 범위 안 → 반영 필요
old_checksum = struct.unpack_from("<I", data, 0x08)[0]
diff = 0
for offset, old_w, new_w in word_changes:
    # WELCOME 범위(0x0AA000~0x0AA8FD)는 XOR 제외
    if 0x0AA000 <= offset < 0x0AA000 + 2560:
        continue
    diff ^= old_w ^ new_w
new_checksum = old_checksum ^ diff
struct.pack_into("<I", data, 0x08, new_checksum)

with open("GP1235_custom_screen.bin", "wb") as f:
    f.write(data)
```

## 체크섬 주의사항

| 영역 | GPNV XOR 범위 | 처리 |
|------|-------------|------|
| 시작 화면 (0x0AA000) | **범위 밖** | 체크섬 영향 없음 (자유 수정) |
| 종료 화면 (0x0A9600) | **범위 안** | GPNV XOR 차분 업데이트 필수 |
| GPRSPAK 인덱스 (0x0842C0) | 범위 안 | 크기 유지 시 변경 불필요 |

### GPRSPAK 리소스 인덱스

펌웨어 `0x0842C0`에 GPRSPAK 인덱스가 있으며, 화면 리소스의 위치를 참조:

| GPRSPAK 엔트리 | 인덱스 값 | 대응 오프셋 |
|---------------|----------|-----------|
| POWER_OFF_LOGOJPG | 0x0129 | 0x0A9600 (GOODBYE) |
| POWER_ON_LOGOJPG | 0x012A | 0x0AA000 (WELCOME) |

**같은 크기 이하**로 교체하면 인덱스 수정 불필요. JPEG 데이터를 제자리에 덮어쓰고 나머지를 `0xFF`로 패딩.

## 검증

1. 패치된 펌웨어를 SD 업그레이드로 적용
2. 전원 ON → 커스텀 시작 화면 표시 확인
3. 전원 OFF → 커스텀 종료 화면 표시 확인
4. 정상 부팅 및 카메라 동작 확인

## 참고

- 원본 시작 화면은 이미 `--brand` 옵션으로 "DORORONG" 커스텀 적용 테스트 완료 (Phase 3)
- LCD는 160x80으로 매우 작아서 단순한 로고/텍스트가 가장 효과적
- 마이크 아이콘(0x084400, 4,358B)은 녹음 모드 UI이므로 별도 교체 가능하나 우선순위 낮음
