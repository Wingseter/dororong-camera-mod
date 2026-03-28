# 펌웨어 분석 진행 기록

> 일시: 2026-03-28
> 파일: firmware_backup_1.bin (1MB)
> SHA256: e19fb6ae6c811d5f47696d054db8f40987cdc54fc44d0880be3d521eac5012ea
> MD5: 72997afac0265ebedb77bf4cf912c7ca

## 1차 분석 결과

### 헤더

- Magic: `GPNV` (Generalplus NV = Non-Volatile)
- 부트로더: `GP DV BootLoader v2.2`
- 칩 감지: `GPDV 64Pin chip detect`

### 메모리 맵

| 영역 | 오프셋 | 크기 | 내용 |
|------|--------|------|------|
| GPNV 헤더 + 부트로더 | 0x000000 - 0x003000 | 12KB | 부트로더 코드 + 헤더 |
| 패딩 | 0x003000 - 0x012000 | 60KB | Zeros |
| **메인 펌웨어** | 0x012000 - 0x0B4000 | 648KB | 코드 + 리소스 |
| 패딩 | 0x0B4000 - 0x0C2000 | 56KB | Zeros |
| 설정/데이터 | 0x0C2000 - 0x0C5000 | 12KB | 추가 데이터 |
| 미사용 | 0x0C5000 - 0x100000 | 236KB | 0xFF (빈 영역) |

### 발견된 핵심 문자열

**부트로더:**
- `GP DV BootLoader v2.2 Entry @ %d MHz`
- `SPI init OK` / `SPI init Fail`
- `SDC init OK` / `SDC init Fail`
- `BootLoader PC Jump to 0x%08x`
- `GPNVBtLdr Recover well done`
- `GPNVNV checksum:0x%08x`

**USB 장치 문자열:**
- `GENPLUS USB-MSDC DISK A 1.00GP-PROD.`
- `GENPLUS USB-CDRM DISK A 1.00GP-PROD.` ← CDROM 모드도 존재!

**JPEG/AVI 인코더:**
- `GPEncoder` (0x07c622, 0x07c9ad)
- `GP$322 Generalplus AviPackerV3 20140916` (0x059ea0)
- `GP$308 Generalplus AVI Parser 2014.04.15` (0x046810)
- `GP$221 Generalplus Multi-Media Parser 2014.04.15` (0x048d24)

**리소스 파일 참조:**
- `BACKGROUND.GPZP` — 배경 이미지
- `SELECTBAR_LONG.GPZP` — UI 선택바
- `SELECT_SHORT.GPZP` — UI 선택바
- `DET_SUB.GPZP` / `DET_SUB1.GPZP` — UI 서브메뉴
- `U_DISK.GPZ` — USB 디스크 모드 리소스
- `PC_CAM.GPZ` — PC 카메라 모드 리소스
- `GPRS.PAK` — 리소스 패키지
- `CAMERA.WAV` — 카메라 셔터 사운드
- `POWERON_AUDIO.WAV` / `POWEROFF_AUDIO.WAV` — 전원 사운드
- `AUDIO_REC_BG.JPG` — 녹음 모드 배경

**메뉴 문자열:**
- `video mode` / `Photo Mode` / `playback mode`
- `Video resolution` / `Photo resolution` / `Photo quality`
- `Brightness`
- `Loop camera` / `Recording`
- `USB function` / `PC camera`
- `Version`
- `NEXT MENU`

**파일 패턴:**
- `MOVI%04d.avi` — 영상 파일명 패턴
- `PV%03d.GPZP` — 프리뷰 파일 패턴
- `CP%02d%02d.GPZP` — 캡처 파일 패턴

### ARM 코드 확인

- 오프셋 0x200: `0xe59ff018` ← **ARM LDR PC 명령어** (ARM 코드 확정!)
- 부트로더 영역에 ARM32 코드 존재

### 중요 발견

1. **`GENPLUS USB-CDRM DISK A`** — CDROM 모드가 펌웨어에 존재! 숨겨진 세 번째 USB 모드일 수 있음
2. **GPZP 파일** — UI 리소스가 GPZP 포맷으로 내장 (18개). 커스터마이징 가능
3. **`Brightness` 메뉴 문자열** — 밝기 설정이 메뉴에 있음
4. **부트로더에 체크섬** — `GPNVNV checksum:0x%08x` → 수정 시 체크섬 재계산 필요
5. **236KB 빈 영역** — 추가 코드/데이터를 넣을 공간 있음
6. **`Upgrade fail` 문자열** — 펌웨어 업그레이드 루틴이 코드에 존재!

## 2차 분석 — USB 디스크립터 및 문자열

### USB Device Descriptor 위치

| 모드 | 오프셋 | VID:PID |
|------|--------|---------|
| MSC (저장장치) | 0x0821CA | 1B3F:0C52 |
| UVC (웹캠) | 0x082246 | 1B3F:2002 |

### UVC Configuration Descriptor

**오프셋 0x082260** — macOS에서 덤프한 것과 동일한 바이너리
- 여기서 Processing Unit bmControls (Brightness) 값, 해상도, 프레임레이트 등을 직접 수정 가능

### USB String Descriptors (0x079E00 영역)

| 오프셋 | 문자열 | 용도 |
|--------|--------|------|
| 0x079E0E | `GENERAL` | Manufacturer |
| 0x079E3E | `GENERAL - UVC ` | Product (웹캠 모드) |
| 0x079E6E | **`Demo 1.00`** | 펌웨어 버전 (String #3) |
| 0x079E9E | `GENERAL - AUDIO` | 오디오 인터페이스 |
| 0x082200 | `Generic USB Mass Storage Device` | Product (저장장치 모드) |

### Demo 1.00 수정 가능!

- 정확한 위치: **0x079E6C** (USB String Descriptor, 20바이트)
- 포맷: `14 03` + UTF-16LE `Demo 1.00`
- 같은 길이 이하의 다른 문자열로 교체 가능 (예: "Custom 1.0")

## 3차 분석 — 카메라/메뉴 문자열

### 카메라 설정 관련 (0x08A000 영역)

| 오프셋 | 문자열 | 의미 |
|--------|--------|------|
| 0x08A3EC | `video mode` | 영상 모드 |
| 0x08A3F7 | `Photo Mode` | 사진 모드 |
| 0x08A402 | `playback mode` | 재생 모드 |
| 0x08A410 | `Settings` | 설정 |
| 0x08A419 | `Video resolution` | 영상 해상도 설정 |
| 0x08A446 | `Loop camera` | 반복 녹화 |
| 0x08A452 | `Recording` | 녹화 중 |
| 0x08A479 | `white balance` | 화이트밸런스 |
| 0x08A5C5 | `Photo resolution` | 사진 해상도 설정 |
| 0x08A5D6 | `Photo quality` | 사진 품질 설정 |
| 0x08A5E4 | `exposure` | 노출 |
| 0x08A67D | `Brightness` | 밝기 |
| 0x08A6B3 | `black and white` | 흑백 필터 |
| 0x08A79A | `volume` | 볼륨 |
| 0x08A7A1 | `NEXT MENU` | 다음 메뉴 |
| 0x08A7C3 | `Format` | 포맷 |
| 0x08A7CA | `Language` | 언어 |
| 0x08A817 | `Version` | 버전 |
| 0x08A80A | `USB function` | USB 기능 |
| 0x08A856 | `PC camera` | PC 카메라 |

### 리소스 파일 참조

| 오프셋 | 파일 | 용도 |
|--------|------|------|
| 0x022370 | `POWER_ON_LOGO.JPG` | 전원 켤 때 로고 |
| 0x028820 | `POWER_OFF_LOGO.JPG` | 전원 끌 때 로고 |
| 0x032A74 | `CAMERA.WAV` | 셔터음 |
| 0x032A80 | `CLICK.WAV` | 클릭음 |
| 0x032A8C | `POWERON_AUDIO.WAV` | 전원 켤 때 소리 |
| 0x032AA0 | `POWEROFF_AUDIO.WAV` | 전원 끌 때 소리 |
| 0x032AB4 | `BEEP.WAV` | 비프음 |
| 0x02F8E4 | `GPRS.PAK` | 리소스 패키지 |
| 0x0278C0 | `U_DISK.GPZ` | USB 디스크 리소스 |
| 0x0278CC | `PC_CAM.GPZ` | PC 카메라 리소스 |

### 파일명 패턴

| 오프셋 | 패턴 | 설명 |
|--------|------|------|
| 0x02630C | `MOVI%04d.avi` | 영상 (MOVI0001.avi ~) |
| 0x026330 | `PICT%04d.jpg` | 사진 (PICT0001.jpg ~) |
| 0x026344 | `RECR%04d.wav` | 녹음 (RECR0001.wav ~) |
| 0x025F00 | `C:\DCIM` | 저장 경로 |

### CDROM 모드

`GENPLUS USB-CDRM DISK A 1.00GP-PROD.` @ 0x082104
- 펌웨어에 CDROM 에뮬레이션 모드 코드가 존재
- 특정 조건에서 USB CDROM으로 인식될 수 있음 (드라이버 자동 설치용?)

### 업그레이드 기능

- `Upgrade fail` @ 0x041DAC
- `Remove SD card and` @ 0x041DBC
- `restart now` @ 0x041DD0
- **펌웨어 내에 업그레이드 루틴이 존재!** SD 카드 기반 업그레이드 코드가 있으나 트리거 조건 미확인

## 수정 가능한 항목 (확인된 것)

| 항목 | 오프셋 | 현재 값 | 수정 방법 |
|------|--------|---------|----------|
| 펌웨어 버전 문자열 | 0x079E6C | "Demo 1.00" | UTF-16LE로 같은 길이 이하 문자열 덮어쓰기 |
| USB VID:PID (UVC) | 0x08224E | 1B3F:2002 | 원하는 값으로 변경 |
| USB VID:PID (MSC) | 0x0821D2 | 1B3F:0C52 | 원하는 값으로 변경 |
| UVC 디스크립터 | 0x082260 | 현재 설정 | 해상도, 컨트롤, 프레임레이트 등 |

## 4차 분석 — SD 카드 업그레이드 루틴 해독

### 업그레이드 파일명 [확인]

펌웨어 바이너리에서 직접 추출:

```
0x041e6c: C:\JH_          ← SD 카드 루트 경로 + 접두어
0x041e74: 5307             ← PCB 모델 번호 (DP-5307B)
0x041e7c: *.bin            ← 와일드카드 확장자
```

**업그레이드 파일명 패턴: `JH_5307*.bin`**

### 업그레이드 메시지 문자열 [확인]

| 오프셋 | 문자열 | 단계 |
|--------|--------|------|
| 0x041A18 | `Upgrading firmware...` | 진행 중 |
| 0x041A30 | `Donot power off now` | 경고 |
| 0x041A48 | `00 %` | 진행률 시작 |
| 0x041DDC | `100%` | 완료 |
| 0x041DAC | `Upgrade fail` | 실패 |
| 0x041DBC | `Remove SD card and` | 실패 후 안내 |
| 0x041DD0 | `restart now` | 재시작 안내 |
| 0x041A4C | `Program error` | 프로그래밍 에러 |

### 펌웨어 빌드 정보 [확인]

```
0x03c43c: "5307 20260129"
```

- PCB: 5307 (= DP-5307B)
- 빌드 날짜: **2026년 01월 29일**
- "Demo 1.00" 문자열과 별개의 내부 빌드 타임스탬프

### 업그레이드 흐름 (코드에서 추론)

```
1. 부팅 시 SD 카드에서 "JH_5307*.bin" 패턴 파일 검색
2. 파일 발견 → "Upgrading firmware..." 표시
3. "Donot power off now" 경고
4. 내부 플래시에 쓰기 (진행률 0% → 100%)
5. 성공 → 재부팅
6. 실패 → "Upgrade fail" → "Remove SD card and restart now"
```

### 의미

1. **SD 카드에 `JH_5307.bin` (또는 `JH_5307*.bin` 패턴)을 넣으면 자동 업그레이드 트리거**
2. 펌웨어를 수정한 후 이 파일명으로 SD에 넣으면 CH341A 없이 업데이트 가능
3. `JH_5307`로 검색하면 같은 보드의 다른 펌웨어 버전을 찾을 수도 있음

## 다음 단계

## 5차 분석 — 메모리 맵, 설정 블록, 메뉴 구조

### 메모리 맵

| 영역 | 주소 | 용도 |
|------|------|------|
| 0x001F8000 | 부트로더 로드 주소 (SRAM) | GPNV 헤더에 명시 |
| 0x8C700000 대역 | DRAM 추정 (2,882회 참조) | 메인 펌웨어 실행 영역 |
| 0x00100000 대역 | SPI 플래시 맵 추정 (3,439회 참조) | 코드/데이터 읽기 |

### 설정 블록 (0xC2000~0xC5000)

512바이트 단위로 반복되는 설정 프로파일 블록 **16개** 발견.

각 블록 구조:
```
Offset 0x00: 07 02 01 xx  ← xx=01(모드A) 또는 00(모드B)
Offset 0x04: 00 08 00 00  ← 해상도 관련?
Offset 0x0F: 02 01 01 01 01  ← 카메라 파라미터
Offset 0x17: 19 01 01     ← 추가 파라미터
Offset 0x29: 03 00 00 08 00 18 00  ← 디스플레이 설정?
Offset 0x38: 01 04        ← 기능 플래그
Offset 0xA0: 01 00 00 00 [checksum 4B]  ← 블록 체크섬
```

체크섬 패턴: 블록마다 다른 4바이트 값 (`53 3d d3 45`, `10 8b 3a e5`, `84 96 e3 72` 등)

### 메뉴 문자열 맵 (0x08A5F0 영역) [확인]

펌웨어가 지원하는 전체 설정 항목:

| 카테고리 | 옵션들 |
|----------|--------|
| 사진 해상도 | `12M`, `8M`, `2M`, `1M`, `VGA` |
| 사진 품질 | `high quality`, `standard`, `economy` |
| 영상 기능 | `Loop camera`, `Recording`, `Continuous shooting` |
| ISP 설정 | `Sharpness`, `colour`, `Brightness`, `exposure`, `white balance` |
| 밝기 옵션 | `automatic`, `one hundred`, `two hundred` |
| 노출 옵션 | `automatic`, `motion`, `Night View` |
| 필터 | `black and white`, `standard` |
| 기타 | `Preview`, `volume`, `Language`, `Format`, `Version` |

**참고**: 일부 메뉴 항목은 LCD UI에서 표시되지 않을 수 있음 (펌웨어 설정으로 숨겨진 메뉴)

## 분석 현황 요약

### 확정된 수정 가능 항목

| # | 항목 | 오프셋 | 현재 값 | 비고 |
|---|------|--------|---------|------|
| 1 | 펌웨어 버전 문자열 | 0x079E6C | "Demo 1.00" (UTF-16LE) | 같은 길이 이하 문자열로 교체 |
| 2 | USB VID:PID (UVC) | 0x08224E | 1B3F:2002 | 변경 가능 |
| 3 | USB VID:PID (MSC) | 0x0821D2 | 1B3F:0C52 | 변경 가능 |
| 4 | UVC Configuration | 0x082260 | 현재 설정 | 해상도, 컨트롤 등 |
| 5 | 설정 블록 | 0x0C2000~0x0C5000 | 16개 프로파일 | 카메라 파라미터 |
| 6 | 메뉴 문자열 | 0x08A3EC~ | 영문 메뉴 | 텍스트 교체 가능 |
| 7 | 리소스 파일 참조 | 여러 위치 | GPZP/WAV/JPG | 리소스 교체 가능 |

### 아직 미확인

| 항목 | 상태 | 다음 단계 |
|------|------|----------|
| Brightness 기본값 정확한 위치 | 설정 블록에 있을 것으로 추정 | Ghidra로 코드 추적 |
| 체크섬 알고리즘 | CRC32/ByteSum/WordSum 모두 불일치 | Ghidra로 역추적 |
| UVC PU bmControls 위치 | UVC config 안에 있으나 정확한 오프셋 미확인 | 디스크립터 재파싱 |
| SD 업그레이드 체크섬 검증 여부 | 코드에서 확인 필요 | Ghidra 분석 |
| GPZP 리소스 포맷 | 매직 바이트만 확인 | 구조 분석 필요 |
| RAM 정확한 크기 | DRAM 존재 추정 (0x8C7 대역) | Ghidra 또는 UART로 확인 |

## 다음 단계

- [ ] Ghidra로 ARM 코드 로드 (베이스 주소 0x001F8000 또는 0x00000000)
- [ ] 업그레이드 함수 역어셈블 → SD 파일 체크섬 검증 로직 확인
- [ ] Brightness 기본값 코드 추적 → 정확한 오프셋 확인
- [ ] 체크섬 알고리즘 역추적 → 수정 후 재계산 방법 확립
- [ ] UVC PU bmControls 정확한 오프셋 재확인
- [ ] GPZP 리소스 포맷 분석
- [ ] `JH_5307` 키워드로 웹 검색 (다른 펌웨어 버전)
- [ ] SD 카드 업그레이드 테스트 준비 (수정된 펌웨어를 JH_5307.bin으로 저장)
