# 부팅/종료음, 셔터음 교체 가이드

> 일시: 2026-03-30
> 대상: GP1235 펌웨어 내장 WAV 오디오 리소스

## 개요

카메라에 내장된 5개 사운드 리소스를 커스텀 오디오로 교체하는 방법.
모든 사운드는 표준 RIFF WAV (PCM) 포맷으로 저장되어 있어 교체가 비교적 간단.

## 리소스 위치 및 규격

| 사운드 | 오프셋 | 총 크기 | 최대 크기 | 샘플레이트 | 비트 | 채널 | 재생 시간 |
|--------|--------|--------|----------|-----------|------|------|----------|
| **부팅음** (POWERON) | `0x0AAA00` | 17,410 B | 17,920 B | 11,025 Hz | 16-bit | Mono | 0.79초 |
| **종료음** (POWEROFF) | `0x0AF000` | 17,410 B | 17,920 B | 11,025 Hz | 16-bit | Mono | 0.79초 |
| **셔터음** (CAMERA) | `0x087E00` | 6,772 B | 7,168 B | 32,000 Hz | 16-bit | Mono | 0.10초 |
| 비프음 (BEEP) | `0x085800` | 4,076 B | 4,096 B | 11,025 Hz | 16-bit | Mono | 0.18초 |
| 클릭음 (CLICK) | `0x086800` | 5,524 B | 5,632 B | 11,025 Hz | 8-bit | Mono | 0.50초 |

- **최대 크기** = 원본 크기 + 다음 리소스까지의 `0xFF`/`0x00` 패딩 영역
- 원본 추출 파일: `analysis/extracted_resources/` 디렉토리

## WAV 파일 구조

### 원본 WAV 청크 구조

**부팅음/종료음** (POWERON, POWEROFF):
```
RIFF (17,402 bytes)
├── fmt  (16 bytes) — PCM, 1ch, 11025Hz, 16-bit
├── LIST (26 bytes) — INFO/ISFT: "Lavf57.8" (FFmpeg 메타데이터)
└── data (17,332 bytes) — 8,666 샘플 = 0.79초
```

**셔터음** (CAMERA):
```
RIFF (6,764 bytes)
├── fmt  (16 bytes) — PCM, 1ch, 32000Hz, 16-bit
├── data (6,694 bytes) — 3,347 샘플 = 0.10초
└── LIST (26 bytes) — INFO/ISFT 메타데이터
```

**비프음** (BEEP):
```
RIFF (4,068 bytes)
├── fmt  (16 bytes) — PCM, 1ch, 11025Hz, 16-bit
└── data (4,032 bytes) — 2,016 샘플 = 0.18초
```

**클릭음** (CLICK):
```
RIFF (5,516 bytes)
├── fmt  (16 bytes) — PCM, 1ch, 11025Hz, 8-bit
└── data (5,480 bytes) — 5,480 샘플 = 0.50초
```

## 커스텀 오디오 제작 규격

### 필수 요구사항

| 항목 | 부팅/종료음 | 셔터음 | 비프/클릭 |
|------|-----------|--------|----------|
| 포맷 | WAV (RIFF PCM) | WAV (RIFF PCM) | WAV (RIFF PCM) |
| 샘플레이트 | **11,025 Hz** | **32,000 Hz** | **11,025 Hz** |
| 비트 깊이 | **16-bit** | **16-bit** | 16-bit / 8-bit |
| 채널 | **Mono** (1ch) | **Mono** (1ch) | **Mono** (1ch) |
| 최대 파일 크기 | **17,920 B** | **7,168 B** | 4,096 / 5,632 B |
| 최대 재생 시간 | ~0.81초 | ~0.11초 | ~0.19 / 0.51초 |

**주의**: 샘플레이트와 비트 깊이를 반드시 원본과 동일하게 맞춰야 함. GP1235의 오디오 DAC가 WAV 헤더를 파싱하여 설정하는지, 아니면 하드코딩된 값으로 재생하는지 미확인. 안전하게 원본 규격을 유지할 것.

### FFmpeg로 변환

```bash
# 부팅음 (11025Hz, 16-bit mono, 최대 0.8초)
ffmpeg -i my_boot_sound.mp3 \
  -ar 11025 -ac 1 -acodec pcm_s16le \
  -t 0.8 \
  custom_poweron.wav

# 종료음
ffmpeg -i my_shutdown_sound.mp3 \
  -ar 11025 -ac 1 -acodec pcm_s16le \
  -t 0.8 \
  custom_poweroff.wav

# 셔터음 (32000Hz, 16-bit mono, 최대 0.1초)
ffmpeg -i my_shutter.mp3 \
  -ar 32000 -ac 1 -acodec pcm_s16le \
  -t 0.1 \
  custom_shutter.wav

# 파일 크기 확인
ls -la custom_*.wav
```

### Audacity로 제작

1. 새 프로젝트 생성 → 프로젝트 샘플레이트 설정 (11025 또는 32000)
2. 오디오 녹음 또는 임포트
3. Tracks → Mix → Mix Stereo Down to Mono
4. 길이 트리밍 (부팅/종료: 0.8초, 셔터: 0.1초)
5. File → Export → WAV (signed 16-bit PCM)
6. 파일 크기가 최대 크기 이하인지 확인

### 크기 계산 공식

```
WAV 파일 크기 = 44 (헤더) + samples × bytes_per_sample
             = 44 + (duration × sample_rate) × (bits / 8) × channels

부팅음 예시:
  max_data = 17920 - 44 = 17876 bytes
  max_samples = 17876 / 2 = 8938
  max_duration = 8938 / 11025 = 0.811초

셔터음 예시:
  max_data = 7168 - 44 = 7124 bytes
  max_samples = 7124 / 2 = 3562
  max_duration = 3562 / 32000 = 0.111초
```

**참고**: LIST 청크(FFmpeg 메타데이터) 없이 최소 헤더(44바이트)만 사용하면 데이터 공간이 약간 더 확보됨. 원본은 LIST 청크 26바이트가 포함되어 실제 PCM 데이터 공간이 줄어듦.

## 적용 방법

### 패치 스크립트 (Python)

```python
#!/usr/bin/env python3
"""GP1235 사운드 리소스 교체 스크립트"""

import struct
import sys

# 리소스 정의
SOUND_RESOURCES = {
    "poweron":  {"offset": 0x0AAA00, "max_size": 17920, "desc": "부팅음"},
    "poweroff": {"offset": 0x0AF000, "max_size": 17920, "desc": "종료음"},
    "shutter":  {"offset": 0x087E00, "max_size":  7168, "desc": "셔터음"},
    "beep":     {"offset": 0x085800, "max_size":  4096, "desc": "비프음"},
    "click":    {"offset": 0x086800, "max_size":  5632, "desc": "클릭음"},
}

# GPNV XOR 제외 영역 (시작 화면만 — 사운드는 전부 범위 안)
GPNV_XOR_EXCLUDED = [
    (0x079E6C, 0x079E6C + 20),
    (0x0AA000, 0x0AA000 + 2560),
]

def is_excluded(offset):
    for start, end in GPNV_XOR_EXCLUDED:
        if start <= offset < end:
            return True
    return False

def validate_wav(wav_data, resource):
    """WAV 파일 기본 검증"""
    if len(wav_data) < 44:
        raise ValueError("WAV 파일이 너무 작습니다 (최소 44바이트)")
    if wav_data[:4] != b'RIFF' or wav_data[8:12] != b'WAVE':
        raise ValueError("유효한 WAV 파일이 아닙니다")
    if len(wav_data) > resource["max_size"]:
        raise ValueError(
            f"WAV 파일 크기 초과: {len(wav_data)} > {resource['max_size']} bytes\n"
            f"최대 {resource['max_size']} bytes 이하로 줄여주세요"
        )
    # PCM 포맷 확인
    audio_fmt = struct.unpack_from("<H", wav_data, 20)[0]
    if audio_fmt != 1:
        raise ValueError(f"PCM 포맷만 지원 (현재: {audio_fmt})")
    channels = struct.unpack_from("<H", wav_data, 22)[0]
    if channels != 1:
        raise ValueError(f"Mono만 지원 (현재: {channels}ch)")
    print(f"  검증 통과: {len(wav_data)} bytes, "
          f"{struct.unpack_from('<I', wav_data, 24)[0]}Hz, "
          f"{struct.unpack_from('<H', wav_data, 34)[0]}bit")

def patch_sound(firmware_path, output_path, replacements):
    """
    replacements: dict of {resource_name: wav_file_path}
    예: {"poweron": "custom_poweron.wav", "shutter": "custom_shutter.wav"}
    """
    with open(firmware_path, "rb") as f:
        data = bytearray(f.read())

    word_changes = []

    for name, wav_path in replacements.items():
        res = SOUND_RESOURCES[name]
        print(f"\n[{res['desc']}] {wav_path} -> 0x{res['offset']:06X}")

        with open(wav_path, "rb") as f:
            wav_data = f.read()

        validate_wav(wav_data, res)

        # 0x00 패딩으로 나머지 채우기
        padded = wav_data + b"\x00" * (res["max_size"] - len(wav_data))

        # 워드 단위로 패치하며 변경사항 기록
        for i in range(0, res["max_size"], 4):
            abs_off = res["offset"] + i
            if abs_off + 4 > len(data):
                break
            old_word = struct.unpack_from("<I", data, abs_off)[0]
            new_word = struct.unpack_from("<I", padded, i)[0]
            if old_word != new_word:
                struct.pack_into("<I", data, abs_off, new_word)
                if not is_excluded(abs_off):
                    word_changes.append((abs_off, old_word, new_word))

        print(f"  패치 완료: {len(wav_data)} bytes 기록")

    # GPNV XOR 차분 업데이트
    if word_changes:
        old_checksum = struct.unpack_from("<I", data, 0x08)[0]
        diff = 0
        for _, old_w, new_w in word_changes:
            diff ^= old_w ^ new_w
        new_checksum = old_checksum ^ diff
        struct.pack_into("<I", data, 0x08, new_checksum)
        print(f"\nGPNV XOR: 0x{old_checksum:08X} -> 0x{new_checksum:08X}")
        print(f"변경된 워드: {len(word_changes)}개")

    with open(output_path, "wb") as f:
        f.write(data)
    print(f"\n저장: {output_path}")

    # SD 업그레이드 파일명 생성
    checksum = sum(data) & 0xFFFFFFFF
    sd_name = f"JH_5307_2026004291200{checksum:08X}.bin"
    print(f"SD 파일명: {sd_name}")

if __name__ == "__main__":
    # 사용 예시
    patch_sound(
        "analysis/GP1235_firmware.bin",
        "analysis/GP1235_custom_sound.bin",
        {
            "poweron": "custom_poweron.wav",
            "poweroff": "custom_poweroff.wav",
            "shutter": "custom_shutter.wav",
        }
    )
```

### settings_patch.py와 병행 사용

사운드 교체와 ISP 설정 패치를 함께 적용하려면:

1. 먼저 `settings_patch.py`로 ISP/브랜딩 패치 적용
2. 그 출력 파일을 사운드 패치 스크립트의 입력으로 사용

```bash
# Step 1: ISP + 브랜딩
python scripts/settings_patch.py analysis/GP1235_firmware.bin \
  --preset phase3 --brand v1.0 -o analysis/GP1235_v1_base.bin

# Step 2: 사운드 교체 (위 스크립트 수정하여)
python scripts/sound_patch.py analysis/GP1235_v1_base.bin \
  -o analysis/GP1235_v1_final.bin \
  --poweron custom_poweron.wav \
  --poweroff custom_poweroff.wav \
  --shutter custom_shutter.wav
```

## 체크섬 주의사항

| 리소스 | GPNV XOR 범위 | 처리 |
|--------|-------------|------|
| 부팅음 (0x0AAA00) | **범위 안** | GPNV XOR 차분 업데이트 필수 |
| 종료음 (0x0AF000) | **범위 안** | GPNV XOR 차분 업데이트 필수 |
| 셔터음 (0x087E00) | **범위 안** | GPNV XOR 차분 업데이트 필수 |
| 비프음 (0x085800) | **범위 안** | GPNV XOR 차분 업데이트 필수 |
| 클릭음 (0x086800) | **범위 안** | GPNV XOR 차분 업데이트 필수 |

**모든 사운드 리소스**가 GPNV XOR 범위 안에 있으므로, 수정 시 반드시 체크섬을 재계산해야 함.

## GPRSPAK 리소스 인덱스

펌웨어 `0x0842C0`의 GPRSPAK 인덱스에 사운드 리소스 엔트리가 있음:

| GPRSPAK 엔트리 | 인덱스 값 | 대응 오프셋 |
|---------------|----------|-----------|
| POWEROFF_AUDIOWAV | 0x012F | 0x0AF000 |
| POWERON_AUDIOWAV | 0x0134 | 0x0AAA00 |

BEEP, CLICK, CAMERA(셔터)는 GPRSPAK에 명시적 엔트리 없음 — 펌웨어 코드에서 하드코딩된 오프셋으로 직접 접근하는 것으로 추정.

**같은 크기 이하**로 교체하면 GPRSPAK 인덱스 수정 불필요.

## 무음 처리

특정 사운드를 없애고 싶으면, PCM 데이터를 모두 0으로 채운 WAV 파일을 생성:

```bash
# 무음 부팅음 (0.1초, 11025Hz, 16-bit mono)
ffmpeg -f lavfi -i "anullsrc=r=11025:cl=mono" \
  -t 0.1 -acodec pcm_s16le \
  silent_poweron.wav
```

또는 Python으로:
```python
import struct, io

def create_silent_wav(sample_rate, bits, duration_s, output_path):
    num_samples = int(sample_rate * duration_s)
    bytes_per_sample = bits // 8
    data_size = num_samples * bytes_per_sample

    header = struct.pack("<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16,
        1,              # PCM
        1,              # mono
        sample_rate,
        sample_rate * bytes_per_sample,
        bytes_per_sample,
        bits,
        b"data", data_size
    )

    with open(output_path, "wb") as f:
        f.write(header)
        f.write(b"\x00" * data_size)

    print(f"Created: {output_path} ({44 + data_size} bytes)")

# 무음 부팅음
create_silent_wav(11025, 16, 0.1, "silent_poweron.wav")
# 무음 셔터음
create_silent_wav(32000, 16, 0.01, "silent_shutter.wav")
```

## 위험도 평가

| 위험 요소 | 수준 | 설명 |
|----------|------|------|
| Brick 위험 | **낮음** | 오디오 영역 손상은 부팅에 영향 없음 (오디오만 깨짐) |
| GPNV 체크섬 | **중간** | 틀리면 부트로더가 거부할 수 있으나, CH341A 복구 가능 |
| 호환성 | **낮음** | 표준 WAV PCM이므로 파싱 실패 가능성 낮음 |
| 복구 | **쉬움** | 원본 펌웨어를 CH341A로 재플래시 |

## 주의사항

1. **샘플레이트 불일치**: DAC가 헤더를 읽지 않고 고정 레이트로 재생하면 피치가 변할 수 있음. 반드시 원본과 동일한 샘플레이트 사용.
2. **LIST 청크**: 원본 POWERON/POWEROFF에는 FFmpeg 메타데이터(LIST/INFO) 청크가 있으나, 없어도 무방할 것으로 추정. 최소 WAV 헤더(44바이트)만으로 더 많은 PCM 데이터 공간 확보 가능.
3. **볼륨**: 카메라에 Volume 설정이 있음 (시스템 메뉴). 커스텀 사운드가 너무 크거나 작으면 이 설정과의 상호작용 확인 필요.
4. **SD 쓰기 순서**: `settings_patch.py` 패치 → 사운드 패치 → SD 파일명 생성 → SD 카드 복사
